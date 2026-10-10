// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const ssdCmdTimeout = 2 * time.Hour

var (
	// binlog-{ip}-{port}-{index}-{yyyymmddHHMMSS}.log.zst; legacy GCS names carry no ip.
	ssdBinlogReg = regexp.MustCompile(`^binlog-(?:(\d{1,3}(?:\.\d{1,3}){3})-)?(\d+)-(\d+)-\d{14}\.log\.(?:zst|lzo)$`)
	// ...-TENDISSSD-FULL-{role}-{ip}-{port}-{yyyymmdd}-{HHMMSS}-{seq}.tar[.split.NNN], seq being the binlog start position.
	ssdFullSeqReg = regexp.MustCompile(`-\d{8}-\d{6}-(\d+)(?:\.tar)?(?:\.split\.\d+)?$`)
)

// ssdRestorer rebuilds rocksdb from a full backup, then replays binlogs up to RecoverAt.
type ssdRestorer struct {
	Job
}

// DoRollback verifies local binlogs against the payload digest before touching any instance,
// then restores, starts and replays each port independently.
func (r *ssdRestorer) DoRollback() error {
	recoverAt, err := time.Parse(time.RFC3339, r.RecoverAt)
	if err != nil {
		return fmt.Errorf("invalid recover_at %q: %v", r.RecoverAt, err)
	}
	redo, err := r.resolvePending()
	if err != nil {
		return err
	}
	if len(redo) == 0 {
		mylog.Logger.Info("RedisRollback %s: all ports already rolled back, nothing to do", r.DestIP)
		return nil
	}
	mylog.Logger.Info("RedisRollback(ssd) dest_ip=%s dest_dir=%s redo=%d total=%d recover_at=%s",
		r.DestIP, r.SaveDir, len(redo), len(r.Instances), r.RecoverAt)

	binlogs := make(map[int][]string, len(redo))
	for _, inst := range redo {
		if binlogs[inst.DestPort], err = LocalBinlogs(r.SaveDir, inst); err != nil {
			return err
		}
	}
	if err = r.Host.InstallTools(); err != nil {
		return err
	}
	backups, err := r.stageBackups(redo)
	if err != nil {
		return err
	}
	if err = r.Host.Prepare(portsOf(redo)); err != nil {
		return err
	}
	return RunBounded(len(redo), StageConcurrency(), func(i int) error {
		inst := redo[i]
		if err := r.restore(inst, backups[inst.DestPort], binlogs[inst.DestPort], recoverAt); err != nil {
			mylog.Logger.Error("RedisRollback(ssd) %s:%d: %v", r.DestIP, inst.DestPort, err)
			return err
		}
		return nil
	})
}

func (r *ssdRestorer) fingerprint(inst InstanceRestore) string {
	return inst.Fingerprint() + "|" + r.RecoverAt
}

// resolvePending skips ports already restored to the same point; any other running port is redone.
func (r *ssdRestorer) resolvePending() ([]InstanceRestore, error) {
	var redo []InstanceRestore
	for _, inst := range r.Instances {
		instDir := r.Host.InstanceDir(inst.DestPort)
		inUse, err := util.CheckPortIsInUse(r.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, err
		}
		if inUse {
			if IsDone(instDir, r.fingerprint(inst)) {
				mylog.Logger.Info("dest_port=%d already rolled back to the same point, skip", inst.DestPort)
				continue
			}
			ClearDone(instDir)
			if err = r.Host.Stop(inst.DestPort); err != nil {
				return nil, err
			}
		}
		redo = append(redo, inst)
	}
	return redo, nil
}

// stageBackups unpacks full backups and returns each port's backup root. Placeholders are skipped.
func (r *ssdRestorer) stageBackups(pending []InstanceRestore) (map[int]string, error) {
	roots := make(map[int]string, len(pending))
	var mu sync.Mutex
	err := RunBounded(len(pending), StageConcurrency(), func(i int) error {
		inst := pending[i]
		if len(inst.FullFiles) == 0 {
			return nil
		}
		files, err := resolveFiles(r.SaveDir, inst)
		if err != nil {
			return err
		}
		workDir, err := unpackBackup(r.SaveDir, files)
		if err != nil {
			return err
		}
		root, err := ssdBackupRoot(workDir)
		if err != nil {
			return err
		}
		mu.Lock()
		roots[inst.DestPort] = root
		mu.Unlock()
		return nil
	})
	return roots, err
}

// restore rebuilds, starts and replays one port, then marks it done and frees its downloads.
func (r *ssdRestorer) restore(inst InstanceRestore, backupRoot string, binlogs []string, recoverAt time.Time) error {
	instDir := r.Host.InstanceDir(inst.DestPort)
	if backupRoot != "" {
		if err := restoreRocksdb(r.Host.MediaName(), backupRoot, ssdDataDir(instDir)); err != nil {
			return err
		}
	}
	if err := r.Host.Start(inst.DestPort); err != nil {
		return err
	}
	if len(binlogs) > 0 {
		startPos, err := fullStartPos(inst.FullFiles)
		if err != nil {
			return err
		}
		workDir := filepath.Join(r.SaveDir, fmt.Sprintf("binlog_replay_%d", inst.DestPort))
		if err = r.replay(inst.DestPort, startPos, recoverAt, binlogs, workDir); err != nil {
			return err
		}
		defer os.RemoveAll(workDir)
	}
	if err := MarkDone(instDir, r.fingerprint(inst)); err != nil {
		return err
	}
	if err := CleanupStaged(r.SaveDir, inst); err != nil {
		mylog.Logger.Warn("RedisRollback cleanup staged files for %d failed: %v", inst.DestPort, err)
	}
	for _, f := range binlogs {
		_ = os.Remove(f)
	}
	return nil
}

// replay applies binlogs in index order. Like v1, error replies are counted and logged rather
// than failing the port, unless every reply of a file is an error.
func (r *ssdRestorer) replay(port int, startPos uint64, recoverAt time.Time, binlogs []string, workDir string) error {
	addr := fmt.Sprintf("%s:%d", r.DestIP, port)
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return err
	}
	cli, err := connectWithin(addr, password, consts.TendisTypeTendisSSDInsance, minLoadDeadline)
	if err != nil {
		return err
	}
	cli.Close()
	if err = os.MkdirAll(workDir, 0755); err != nil {
		return err
	}

	endMs := replayEndMs(recoverAt)
	var total replyStats
	for _, f := range binlogs {
		base := filepath.Base(f)
		if err = decompressFile(f, filepath.Join(workDir, base)); err != nil {
			return fmt.Errorf("decompress %s: %v", base, err)
		}
		logFile := filepath.Join(workDir, strings.TrimSuffix(base, filepath.Ext(base)))
		cmdFile, outFile := logFile+".cmd", logFile+".out"

		if err = parseBinlog(logFile, cmdFile, startPos, endMs); err != nil {
			return fmt.Errorf("parse binlog %s failed: %v", base, err)
		}
		if err = applyCommands(r.DestIP, port, password, cmdFile, outFile); err != nil {
			return fmt.Errorf("apply binlog %s failed: %v", base, err)
		}
		stats, err := readReplies(outFile)
		if err != nil {
			return fmt.Errorf("apply binlog %s: %v", base, err)
		}
		mylog.Logger.Info("%s applied %s: %d reply lines, %d errors, samples %q",
			addr, base, stats.Lines, stats.Errors, stats.Samples)
		if stats.Lines > 0 && stats.Errors == stats.Lines {
			return fmt.Errorf("apply binlog %s: all %d replies are errors, samples %q",
				base, stats.Lines, stats.Samples)
		}
		total.add(stats)
		_ = os.Remove(logFile)
		_ = os.Remove(cmdFile)
		_ = os.Remove(outFile)
	}
	if total.Errors > 0 {
		mylog.Logger.Warn("%s replayed %d binlogs with %d error replies in %d reply lines, "+
			"writes behind these errors may be missing, samples %q",
			addr, len(binlogs), total.Errors, total.Lines, total.Samples)
	} else {
		mylog.Logger.Info("%s replayed %d binlogs, %d reply lines, no errors", addr, len(binlogs), total.Lines)
	}
	return nil
}

// replayEndMs is the --end-datetime for recoverAt. The bound is exclusive, so like v1 it is one
// second later to keep the writes made within the recoverAt second.
func replayEndMs(recoverAt time.Time) int64 {
	return recoverAt.Add(time.Second).UnixMilli()
}

func parseBinlog(logFile, cmdFile string, startPos uint64, endMs int64) error {
	out, err := os.Create(cmdFile)
	if err != nil {
		return err
	}
	defer out.Close()
	ctx, cancel := context.WithTimeout(context.Background(), ssdCmdTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, consts.TredisBinlogBin,
		fmt.Sprintf("--start-position=%d", startPos), fmt.Sprintf("--end-datetime=%d", endMs), logFile)
	cmd.Env = append(os.Environ(), ssdToolEnv()...)
	var stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = out, &stderr
	if err = cmd.Run(); err != nil || strings.Contains(stderr.String(), "ERR:") {
		return fmt.Errorf("%v %s", err, stderr.String())
	}
	return nil
}

// applyCommands feeds cmdFile to redis-cli. The password goes in as a leading AUTH on stdin
// so that it never shows up in the process arguments.
func applyCommands(ip string, port int, password, cmdFile, outFile string) error {
	in, err := os.Open(cmdFile)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(outFile)
	if err != nil {
		return err
	}
	defer out.Close()
	ctx, cancel := context.WithTimeout(context.Background(), ssdCmdTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, consts.RedisCliBin, "--no-raw", "-h", ip, "-p", strconv.Itoa(port))
	var stderr bytes.Buffer
	cmd.Stdin = io.MultiReader(strings.NewReader(authLine(password)), in)
	cmd.Stdout, cmd.Stderr = out, &stderr
	if err = cmd.Run(); err != nil {
		return fmt.Errorf("%v %s", err, stderr.String())
	}
	return nil
}

// authLine quotes the password the way redis-cli splits stdin lines: inside double quotes,
// with \" \\ and \xHH escapes.
func authLine(password string) string {
	var b strings.Builder
	b.WriteString(`AUTH "`)
	for i := 0; i < len(password); i++ {
		switch c := password[i]; {
		case c == '"' || c == '\\':
			b.WriteByte('\\')
			b.WriteByte(c)
		case c >= 0x20 && c < 0x7f:
			b.WriteByte(c)
		default:
			fmt.Fprintf(&b, `\x%02x`, c)
		}
	}
	b.WriteString("\"\n")
	return b.String()
}

// LocalBinlogs returns inst's downloaded binlogs in replay order, after checking that they are
// exactly the chain the plan was built on: same count and same fingerprint.
func LocalBinlogs(saveDir string, inst InstanceRestore) ([]string, error) {
	if inst.BinlogCount == 0 {
		return nil, nil
	}
	type binlog struct {
		path  string
		index int64
	}
	paths, err := filepath.Glob(filepath.Join(saveDir, "binlog-*"))
	if err != nil {
		return nil, err
	}
	rng := inst.BinlogRange
	var found []binlog
	for _, p := range paths {
		m := ssdBinlogReg.FindStringSubmatch(filepath.Base(p))
		if m == nil || (m[1] != "" && m[1] != inst.SourceIP) || m[2] != strconv.Itoa(inst.SourcePort) {
			continue
		}
		idx, _ := strconv.ParseInt(m[3], 10, 64)
		if idx >= rng.FirstIndex && idx <= rng.LastIndex {
			found = append(found, binlog{p, idx})
		}
	}
	sort.Slice(found, func(i, j int) bool {
		if found[i].index != found[j].index {
			return found[i].index < found[j].index
		}
		return found[i].path < found[j].path
	})

	files := make([]string, len(found))
	names := make([]string, len(found))
	seen := make(map[int64]int, len(found))
	for i, b := range found {
		files[i], names[i] = b.path, filepath.Base(b.path)
		seen[b.index]++
	}
	if len(found) == inst.BinlogCount && BinlogFingerprint(names) == inst.BinlogFingerprint {
		return files, nil
	}
	var missing, duplicate []int64
	for idx := rng.FirstIndex; idx <= rng.LastIndex; idx++ {
		switch n := seen[idx]; {
		case n == 0:
			missing = append(missing, idx)
		case n > 1:
			duplicate = append(duplicate, idx)
		}
	}
	return nil, fmt.Errorf("binlogs of %s:%d in %s differ from the plan: want %d as %s, got %d, "+
		"missing %v (planned gaps included), duplicate %v",
		inst.SourceIP, inst.SourcePort, saveDir, inst.BinlogCount, inst.BinlogSegments,
		len(found), missing, duplicate)
}

// BinlogFingerprint is sha256 over binlog basenames in index order, joined by newlines.
// The planner computes the same digest, so any drift between plan and disk is caught.
func BinlogFingerprint(names []string) string {
	sum := sha256.Sum256([]byte(strings.Join(names, "\n")))
	return hex.EncodeToString(sum[:])
}

// fullStartPos parses the binlog start position the full backup was taken at.
func fullStartPos(files []string) (uint64, error) {
	for _, f := range files {
		if m := ssdFullSeqReg.FindStringSubmatch(filepath.Base(f)); m != nil {
			return strconv.ParseUint(m[1], 10, 64)
		}
	}
	return 0, fmt.Errorf("no binlog start position in full backup names %v", files)
}

// ssdBackupRoot locates the rocksdb backup inside workDir: the tar holds one directory named
// after the backup. Backups with more than one version (meta/2) are not restorable.
func ssdBackupRoot(workDir string) (string, error) {
	root := workDir
	if !util.FileExists(filepath.Join(root, "meta")) {
		entries, err := os.ReadDir(workDir)
		if err != nil {
			return "", err
		}
		if len(entries) != 1 || !entries[0].IsDir() {
			return "", fmt.Errorf("no tendisssd backup found in %s", workDir)
		}
		root = filepath.Join(workDir, entries[0].Name())
	}
	if !util.FileExists(filepath.Join(root, "meta")) {
		return "", fmt.Errorf("no meta dir in tendisssd backup %s", root)
	}
	if util.FileExists(filepath.Join(root, "meta", "2")) {
		return "", fmt.Errorf("tendisssd backup %s holds more than one version", root)
	}
	return root, nil
}

// ssdDataDir reads the dir directive from redis.conf; rocksdb lives in dir/rocksdb.
func ssdDataDir(instDir string) string {
	if raw, err := os.ReadFile(filepath.Join(instDir, "redis.conf")); err == nil {
		for _, line := range strings.Split(string(raw), "\n") {
			if fields := strings.Fields(line); len(fields) == 2 && fields[0] == "dir" {
				return fields[1]
			}
		}
	}
	return filepath.Join(instDir, "data")
}

// ssdRestoreTool picks the rocksdb restore command for the media: v1.2 and v1.3 ship different tools.
func ssdRestoreTool(media string) (string, error) {
	bin := filepath.Join(consts.UsrLocal, "redis", "bin")
	switch {
	case strings.Contains(media, "-v1.2."):
		return filepath.Join(bin, "rr_restore_backup") + " %s %s 1", nil
	case strings.Contains(media, "-v1.3."):
		return filepath.Join(bin, "tredisrestore") + " %s %s", nil
	}
	return "", fmt.Errorf("no rocksdb restore tool for media %s", media)
}

func ssdToolEnv() []string {
	deps := filepath.Join(consts.UsrLocal, "redis", "bin", "deps")
	return []string{
		fmt.Sprintf("LD_PRELOAD=%s/libjemalloc.so", deps),
		fmt.Sprintf("LD_LIBRARY_PATH=%s:%s", os.Getenv("LD_LIBRARY_PATH"), deps),
	}
}

// restoreRocksdb replaces dataDir/rocksdb with the one rebuilt from backupRoot.
func restoreRocksdb(media, backupRoot, dataDir string) error {
	tool, err := ssdRestoreTool(media)
	if err != nil {
		return err
	}
	rocksdbDir := filepath.Join(dataDir, "rocksdb")
	if err = os.RemoveAll(rocksdbDir); err != nil {
		return err
	}
	cmd := strings.Join(ssdToolEnv(), " ") + " " + fmt.Sprintf(tool, backupRoot, rocksdbDir)
	mylog.Logger.Info("restore rocksdb: %s", cmd)
	out, err := util.RunBashCmd(cmd, "", nil, ssdCmdTimeout)
	if err != nil || strings.Contains(out, "ERR:") {
		return fmt.Errorf("restore rocksdb from %s failed: %v %s", backupRoot, err, out)
	}
	if !util.FileExists(rocksdbDir) {
		return fmt.Errorf("restore rocksdb from %s produced no %s", backupRoot, rocksdbDir)
	}
	return util.LocalDirChownMysql(dataDir)
}

const replyErrorSamples = 5

// replyStats counts redis-cli --no-raw output lines, not commands: an array reply spans
// several lines, so the error ratio means little and only an all-error file fails the port.
type replyStats struct {
	Lines   int
	Errors  int
	Samples []string
}

func (s *replyStats) add(o replyStats) {
	s.Lines += o.Lines
	s.Errors += o.Errors
	for _, line := range o.Samples {
		if len(s.Samples) >= replyErrorSamples {
			break
		}
		s.Samples = append(s.Samples, line)
	}
}

// readReplies summarizes out, whose first line answers the AUTH applyCommands prepends.
func readReplies(out string) (replyStats, error) {
	var st replyStats
	f, err := os.Open(out)
	if err != nil {
		return st, err
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 64*1024), 64*1024*1024)
	if !scanner.Scan() {
		return st, fmt.Errorf("no reply to AUTH: %v", scanner.Err())
	}
	if line := scanner.Text(); line != "OK" {
		return st, fmt.Errorf("auth failed: %s", line)
	}
	for scanner.Scan() {
		line := scanner.Text()
		st.Lines++
		if strings.HasPrefix(line, "(error)") {
			st.Errors++
			if len(st.Samples) < replyErrorSamples {
				st.Samples = append(st.Samples, line)
			}
		}
	}
	return st, scanner.Err()
}
