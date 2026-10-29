// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
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

const (
	ssdCmdTimeout = 2 * time.Hour
	// ssdApplyTimeout bounds each read and write of a replay connection, not the whole replay.
	ssdApplyTimeout = 10 * time.Minute
)

var (
	// binlog-{ip}-{port}-{index}-{yyyymmddHHMMSS}.log.zst; legacy GCS names carry no ip.
	ssdBinlogReg = regexp.MustCompile(`^binlog-(?:(\d{1,3}(?:\.\d{1,3}){3})-)?(\d+)-(\d+)-\d{14}\.log\.(?:zst|lzo)$`)
	// ...-TENDISSSD-FULL-{role}-{ip}-{port}-{yyyymmdd}-{HHMMSS}-{seq}.tar[.split.NNN], seq being binlogsize's end seq.
	ssdFullSeqReg = regexp.MustCompile(`-\d{8}-\d{6}-(\d+)(?:\.tar)?(?:\.split\.\d+)?$`)
)

// ssdRestorer rebuilds rocksdb from a full backup, then replays binlogs up to RecoverAt.
type ssdRestorer struct {
	Job
}

// DoRollback verifies local binlogs against the payload digest before touching any instance.
// Then every port goes through unpack, restore, start and replay on its own, the ports with the
// most binlog bytes first, so later ports unpack while earlier ones replay.
func (r *ssdRestorer) DoRollback() error {
	recoverAt, err := time.Parse(time.RFC3339, r.RecoverAt)
	if err != nil {
		return fmt.Errorf("invalid recover_at %q: %v", r.RecoverAt, err)
	}
	limits := HostLimits(r.MaxConcurrency)
	report := newHostReport(r.DestIP, "tendisssd", r.Instances)
	defer report.logResult()

	redo, err := r.resolvePending(report)
	if err != nil {
		return err
	}
	if len(redo) == 0 {
		mylog.Logger.Info("RedisRollback %s: all ports already rolled back, nothing to do", r.DestIP)
		return nil
	}

	binlogs := make(map[int][]string, len(redo))
	plans := make(map[int]portPlan, len(redo))
	for _, inst := range redo {
		if binlogs[inst.DestPort], err = LocalBinlogs(r.SaveDir, inst); err != nil {
			report.port(inst.DestPort).finish(err)
			return err
		}
		var full []string
		for _, name := range inst.FullFiles {
			full = append(full, filepath.Join(r.SaveDir, filepath.Base(name)))
		}
		plans[inst.DestPort] = portPlan{fullBytes: totalSize(full), binlogs: len(binlogs[inst.DestPort]),
			binlogBytes: totalSize(binlogs[inst.DestPort])}
	}
	sortLongestFirst(redo, plans)

	if err = r.Host.InstallTools(); err != nil {
		return err
	}
	if err = r.Host.Prepare(portsOf(redo)); err != nil {
		return err
	}
	for _, inst := range redo {
		plan := plans[inst.DestPort]
		plan.memory = SSDMemory(confFile(r.Host.InstanceDir(inst.DestPort)))
		plans[inst.DestPort] = plan
	}
	replaying := limits.Replay(len(redo))
	report.logPlan(limits, plans, r.UnpackDir)
	mylog.Logger.Info("RedisRollback(ssd) dest=%s recover_at=%s replay=%d order=%v",
		r.DestIP, r.RecoverAt, replaying, portsOf(redo))

	window := newMemWindow(limits.MemAvailable, len(redo))
	replaySlots := make(chan struct{}, replaying)
	var wg sync.WaitGroup
	var errs errCollector
	errs.add(RunBounded(len(redo), limits.Unpack, func(i int) error {
		inst := redo[i]
		p := report.port(inst.DestPort)
		if err := r.prepare(inst, p, window); err != nil {
			p.finish(err)
			return err
		}
		// Replay elsewhere so this slot unpacks the next port meanwhile.
		wg.Add(1)
		go func() {
			defer wg.Done()
			replaySlots <- struct{}{}
			err := r.replayAndMark(inst, p, binlogs[inst.DestPort], recoverAt)
			<-replaySlots
			p.finish(err)
			errs.add(err)
		}()
		return nil
	}))
	wg.Wait()
	return errs.err
}

// sortLongestFirst orders ports by binlog bytes, largest first, to shorten the host's total time.
func sortLongestFirst(instances []InstanceRestore, plans map[int]portPlan) {
	sort.SliceStable(instances, func(i, j int) bool {
		return plans[instances[i].DestPort].binlogBytes > plans[instances[j].DestPort].binlogBytes
	})
}

func (r *ssdRestorer) fingerprint(inst InstanceRestore) string {
	return inst.Fingerprint() + "|" + r.RecoverAt
}

// resolvePending skips ports already restored to the same point; any other running port is redone.
func (r *ssdRestorer) resolvePending(report *hostReport) ([]InstanceRestore, error) {
	var redo []InstanceRestore
	for _, inst := range r.Instances {
		instDir := r.Host.InstanceDir(inst.DestPort)
		inUse, err := util.CheckPortIsInUse(r.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, err
		}
		if inUse {
			if IsDone(instDir, r.fingerprint(inst)) {
				newPortLog(r.DestIP, inst).Info("already rolled back to the same point, skip")
				report.skipped(inst.DestPort)
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

// prepare unpacks and restores rocksdb, then starts the instance once its caches fit in memory.
// The unpacked backup goes as soon as rocksdb is rebuilt, so only the ports unpacking hold both
// on the data disk. Placeholders without backup files start empty.
func (r *ssdRestorer) prepare(inst InstanceRestore, p *portReport, window *memWindow) error {
	log := newPortLog(r.DestIP, inst)
	instDir := r.Host.InstanceDir(inst.DestPort)
	workDir := r.portWorkDir(inst.DestPort)
	if len(inst.FullFiles) > 0 {
		var root string
		err := p.timed(stageUnpack, func() error {
			files, err := resolveFiles(r.SaveDir, inst)
			if err != nil {
				return err
			}
			log.Info("unpack files=%v into %s", inst.FullFiles, workDir)
			cpu, err := unpackBackup(files, workDir)
			p.addCPU(stageUnpack, cpu)
			if err != nil {
				return err
			}
			root, err = ssdBackupRoot(workDir)
			return err
		})
		if err != nil {
			log.Error("unpack failed: %v", err)
			return err
		}
		err = p.timed(stageRestore, func() error {
			return restoreRocksdb(log, r.Host.MediaName(), root, ssdDataDir(instDir), workDir)
		})
		if err != nil {
			log.Error("%v", err)
			return err
		}
		// rocksdb now holds a copy; a retry unpacks again from the downloads.
		if err = os.RemoveAll(workDir); err != nil {
			log.Warn("remove unpacked backup %s failed: %v", workDir, err)
		}
	}
	need := SSDMemory(confFile(instDir))
	if err := window.reserve(need); err != nil {
		err = fmt.Errorf("start %s:%d: %v", r.DestIP, inst.DestPort, err)
		log.Error("%v", err)
		return err
	}
	if err := p.timed(stageStart, func() error { return r.Host.Start(inst.DestPort) }); err != nil {
		window.unreserve(need)
		return err
	}
	return nil
}

// replayAndMark replays inst's binlogs, then marks it done and frees its downloads.
func (r *ssdRestorer) replayAndMark(inst InstanceRestore, p *portReport, binlogs []string,
	recoverAt time.Time) error {
	log := newPortLog(r.DestIP, inst)
	// Earlier attempts on older media kept the decompressed binlog and its commands here.
	_ = os.RemoveAll(filepath.Join(r.SaveDir, fmt.Sprintf("binlog_replay_%d", inst.DestPort)))
	if len(binlogs) > 0 {
		if err := r.replay(log, p, inst, recoverAt, binlogs); err != nil {
			log.Error("%v", err)
			return err
		}
	}
	instDir := r.Host.InstanceDir(inst.DestPort)
	if err := MarkDone(instDir, r.fingerprint(inst)); err != nil {
		return err
	}
	if err := CleanupStaged(r.SaveDir, r.portWorkDir(inst.DestPort), inst); err != nil {
		log.Warn("cleanup staged files failed: %v", err)
	}
	for _, f := range binlogs {
		_ = os.Remove(f)
	}
	return nil
}

// replay decodes binlogs in index order and sends their commands over one connection. Like v1,
// error replies are counted and logged rather than failing the port, unless every reply of a
// file is an error. Each file is streamed straight into the connection, so nothing is written
// to disk between decoding and sending.
func (r *ssdRestorer) replay(log portLog, p *portReport, inst InstanceRestore, recoverAt time.Time,
	binlogs []string) error {
	port := inst.DestPort
	addr := fmt.Sprintf("%s:%d", r.DestIP, port)
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return err
	}
	cli, err := connectWithin(addr, password, consts.TendisTypeTendisSSDInsance, minLoadDeadline)
	if err != nil {
		return err
	}
	startPos, err := replayStartPos(log, func() (uint64, error) {
		size, err := cli.TendisSSDBinlogSize()
		return size.EndSeq, err
	}, inst.FullFiles)
	cli.Close()
	if err != nil {
		return err
	}
	applyCli, err := myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeTendisSSDInsance,
		ssdApplyTimeout)
	if err != nil {
		return err
	}
	defer applyCli.Close()

	endMs := replayEndMs(recoverAt)
	var total replyStats
	var seen bool
	var firstSeq, lastSeq int64
	for _, file := range binlogs {
		base := filepath.Base(file)
		begin := time.Now()
		var applyWall time.Duration
		var fileStats replyStats
		pipe := &commandPipe{
			exec: timedExec{exec: redisPipe{cli: applyCli.InstanceClient}, onBatch: func(d time.Duration) {
				applyWall += d
				p.add(stageApply, d)
			}},
			onReply: func(args []string, reply error) error {
				fileStats.Lines++
				if reply != nil {
					fileStats.record(reply.Error(), commandPreview(args))
				}
				return nil
			},
		}
		stats, cpu, err := decodeSSDFile(file, startPos, endMs, func(rec *ssdBinlogRecord) error {
			args, skip, err := rec.command(time.Now().UnixMilli())
			if err != nil {
				return fmt.Errorf("seq %d: %v", rec.seq, err)
			}
			if skip {
				return nil
			}
			return pipe.add(args)
		})
		p.addCPU(stageParse, cpu)
		p.add(stageParse, stats.readTime)
		p.add(stageDecode, time.Since(begin)-stats.readTime-applyWall)
		if err == nil {
			err = pipe.flush()
		}
		if err != nil {
			return fmt.Errorf("binlog %s: %w", base, err)
		}
		log.Info("applied %s: %s", base, fileStats.summary())
		if fileStats.Lines > 0 && fileStats.Errors == fileStats.Lines {
			return fmt.Errorf("binlog %s: all %d replies are errors, samples %q",
				base, fileStats.Lines, fileStats.samples())
		}
		total.add(fileStats)
		if stats.records > 0 {
			if !seen {
				firstSeq, seen = stats.firstSeq, true
			}
			lastSeq = stats.lastSeq
		}
	}
	p.replayed(len(binlogs), total)
	if total.Errors > total.Expected {
		log.Warn("replayed %d binlogs, seq %d -> %d, writes behind unexpected errors may be missing: %s",
			len(binlogs), firstSeq, lastSeq, total.summary())
	} else {
		log.Info("replayed %d binlogs, seq %d -> %d: %s", len(binlogs), firstSeq, lastSeq, total.summary())
	}
	return nil
}

// replayStartPos is the first binlog seq not yet in the restored snapshot. The seq in the full
// backup name is the last one already written when the backup began, so replay starts after it.
// The restored instance's own end seq is preferred; both are logged when they differ.
func replayStartPos(log portLog, endSeq func() (uint64, error), fullFiles []string) (uint64, error) {
	nameSeq, nameErr := fullStartPos(fullFiles)
	seq, err := endSeq()
	if err == nil && seq == 0 {
		err = fmt.Errorf("binlogsize returned end seq 0")
	}
	switch {
	case err != nil && nameErr != nil:
		return 0, fmt.Errorf("no replay start position, binlogsize: %v; %v", err, nameErr)
	case err != nil:
		log.Warn("binlogsize unavailable (%v), start replay after full backup seq %d", err, nameSeq)
		return nameSeq + 1, nil
	case nameErr != nil:
		log.Warn("%v, start replay after restored end seq %d", nameErr, seq)
		return seq + 1, nil
	case seq < nameSeq:
		// Everything up to nameSeq is in the snapshot; starting earlier would replay it again.
		log.Warn("restored end seq %d is behind full backup seq %d, start replay after %d", seq, nameSeq, nameSeq)
		return nameSeq + 1, nil
	case seq > nameSeq:
		log.Warn("restored end seq %d is ahead of full backup seq %d, start replay after %d", seq, nameSeq, seq)
	default:
		log.Info("restored end seq %d matches full backup, start replay after it", seq)
	}
	return seq + 1, nil
}

// replayEndMs is the exclusive end of the replay window: one second after recoverAt keeps the
// writes made within the recoverAt second, as v1 does.
func replayEndMs(recoverAt time.Time) int64 {
	return recoverAt.Add(time.Second).UnixMilli()
}

const previewBytes = 64

// commandPreview shows a command's name and key for error samples.
func commandPreview(args []string) string {
	if len(args) > 2 {
		args = args[:2]
	}
	parts := make([]string, len(args))
	for i, arg := range args {
		parts[i] = strconv.Quote(previewLine(arg))
	}
	return strings.Join(parts, " ")
}

func previewLine(s string) string {
	s = strings.TrimRight(s, "\r\n")
	if len(s) > previewBytes {
		return s[:previewBytes] + "..."
	}
	return s
}

// LocalBinlogs returns inst's downloaded binlogs in replay order, after checking that they are
// exactly the chain the plan was built on: same count and same fingerprint.
func LocalBinlogs(saveDir string, inst InstanceRestore) ([]string, error) {
	if inst.BinlogCount == 0 {
		return nil, nil
	}
	paths, err := filepath.Glob(filepath.Join(saveDir, "binlog-*"))
	if err != nil {
		return nil, err
	}
	var found []localBinlog
	for _, p := range paths {
		m := ssdBinlogReg.FindStringSubmatch(filepath.Base(p))
		if m == nil || (m[1] != "" && m[1] != inst.SourceIP) || m[2] != strconv.Itoa(inst.SourcePort) {
			continue
		}
		idx, _ := strconv.ParseInt(m[3], 10, 64)
		found = append(found, localBinlog{p, idx})
	}
	return checkChain(saveDir, found, chainDigest{
		label:       fmt.Sprintf("%s:%d", inst.SourceIP, inst.SourcePort),
		rng:         inst.BinlogRange,
		count:       inst.BinlogCount,
		fingerprint: inst.BinlogFingerprint,
		segments:    inst.BinlogSegments,
	})
}

type localBinlog struct {
	path  string
	index int64
}

// chainDigest is what the plan says one binlog chain holds.
type chainDigest struct {
	label       string
	rng         BinlogRange
	count       int
	fingerprint string
	segments    string
}

// checkChain keeps the binlogs of found within the planned range, in index order, and requires
// them to be the planned chain.
func checkChain(saveDir string, found []localBinlog, d chainDigest) ([]string, error) {
	var chain []localBinlog
	for _, b := range found {
		if b.index >= d.rng.FirstIndex && b.index <= d.rng.LastIndex {
			chain = append(chain, b)
		}
	}
	sort.Slice(chain, func(i, j int) bool {
		if chain[i].index != chain[j].index {
			return chain[i].index < chain[j].index
		}
		return chain[i].path < chain[j].path
	})

	files := make([]string, len(chain))
	names := make([]string, len(chain))
	seen := make(map[int64]int, len(chain))
	for i, b := range chain {
		files[i], names[i] = b.path, filepath.Base(b.path)
		seen[b.index]++
	}
	if len(chain) == d.count && BinlogFingerprint(names) == d.fingerprint {
		return files, nil
	}
	var missing, duplicate []int64
	for idx := d.rng.FirstIndex; idx <= d.rng.LastIndex; idx++ {
		switch n := seen[idx]; {
		case n == 0:
			missing = append(missing, idx)
		case n > 1:
			duplicate = append(duplicate, idx)
		}
	}
	return nil, fmt.Errorf("binlogs of %s in %s differ from the plan: want %d as %s, got %d, "+
		"missing %v (planned gaps included), duplicate %v",
		d.label, saveDir, d.count, d.segments, len(chain), missing, duplicate)
}

// BinlogFingerprint is sha256 over binlog basenames in index order, joined by newlines.
// The planner computes the same digest, so any drift between plan and disk is caught.
func BinlogFingerprint(names []string) string {
	sum := sha256.Sum256([]byte(strings.Join(names, "\n")))
	return hex.EncodeToString(sum[:])
}

// fullStartPos parses the last binlog seq written when the full backup began.
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
	return confDir(instDir, filepath.Join(instDir, "data"))
}

// confDir is the dir directive of the instance's redis.conf, or fallback without one.
func confDir(instDir, fallback string) string {
	if raw, err := os.ReadFile(confFile(instDir)); err == nil {
		for _, line := range strings.Split(string(raw), "\n") {
			if fields := strings.Fields(line); len(fields) == 2 && fields[0] == "dir" {
				return fields[1]
			}
		}
	}
	return fallback
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

// restoreRocksdb replaces dataDir/rocksdb with the one rebuilt from backupRoot. The tool's output
// is kept in workDir.
func restoreRocksdb(log portLog, media, backupRoot, dataDir, workDir string) error {
	tool, err := ssdRestoreTool(media)
	if err != nil {
		return err
	}
	rocksdbDir := filepath.Join(dataDir, "rocksdb")
	if err = os.RemoveAll(rocksdbDir); err != nil {
		return err
	}
	cmd := strings.Join(ssdToolEnv(), " ") + " " + fmt.Sprintf(tool, backupRoot, rocksdbDir)
	log.Info("restore rocksdb: %s", cmd)
	out, err := util.RunBashCmd(cmd, "", nil, ssdCmdTimeout)
	if err != nil || strings.Contains(out, "ERR:") {
		return fmt.Errorf("restore rocksdb from %s failed: %v %s", backupRoot, err,
			keepOutput(workDir, "restore.out", []byte(out)))
	}
	if !util.FileExists(rocksdbDir) {
		return fmt.Errorf("restore rocksdb from %s produced no %s", backupRoot, rocksdbDir)
	}
	return util.LocalDirChownMysql(dataDir)
}

const replyErrorSamples = 5

// expectedReplyError marks keys that expired between recover_at and the replay: tredisbinlog
// turns their absolute expiry into a TTL relative to now, which is no longer positive.
const expectedReplyError = "invalid expire time"

// replyStats counts the replies of a replay, one per command; Lines is that count. Errors includes
// Expected; Kinds counts every error by errorKind. Samples show the reply and its command.
type replyStats struct {
	Lines           int
	Errors          int
	Expected        int
	Kinds           map[string]int
	Samples         []string
	ExpectedSamples []string
}

func (s *replyStats) record(reply, command string) {
	s.Errors++
	kind := errorKind(reply)
	line := fmt.Sprintf("(error) %s <- %s", reply, command)
	if s.Kinds == nil {
		s.Kinds = map[string]int{}
	}
	s.Kinds[kind]++
	if kind == expectedReplyError {
		s.Expected++
		s.ExpectedSamples = appendSample(s.ExpectedSamples, line)
		return
	}
	s.Samples = appendSample(s.Samples, line)
}

func (s *replyStats) add(o replyStats) {
	s.Lines += o.Lines
	s.Errors += o.Errors
	s.Expected += o.Expected
	for kind, n := range o.Kinds {
		if s.Kinds == nil {
			s.Kinds = map[string]int{}
		}
		s.Kinds[kind] += n
	}
	for _, line := range o.Samples {
		s.Samples = appendSample(s.Samples, line)
	}
	for _, line := range o.ExpectedSamples {
		s.ExpectedSamples = appendSample(s.ExpectedSamples, line)
	}
}

// samples puts errors that need attention first and fills the rest with expected ones.
func (s *replyStats) samples() []string {
	out := append([]string{}, s.Samples...)
	for _, line := range s.ExpectedSamples {
		out = appendSample(out, line)
	}
	return out
}

func (s *replyStats) summary() string {
	if s.Errors == 0 {
		return fmt.Sprintf("%d commands, no errors", s.Lines)
	}
	return fmt.Sprintf("%d commands, %d errors (%d need attention, %d expected %q), kinds %v, samples %q",
		s.Lines, s.Errors, s.Errors-s.Expected, s.Expected, expectedReplyError, s.Kinds, s.samples())
}

func appendSample(samples []string, line string) []string {
	if len(samples) >= replyErrorSamples {
		return samples
	}
	return append(samples, line)
}

// errorKind groups an error reply by its prefix: the error code, plus the next two words for the
// generic ERR code, e.g. "ERR unknown command" or "WRONGTYPE".
func errorKind(reply string) string {
	msg := strings.TrimSpace(reply)
	if strings.Contains(msg, expectedReplyError) {
		return expectedReplyError
	}
	words := strings.Fields(msg)
	switch {
	case len(words) == 0:
		return "(empty)"
	case words[0] != "ERR":
		return words[0]
	case len(words) > 3:
		words = words[:3]
	}
	return strings.Join(words, " ")
}
