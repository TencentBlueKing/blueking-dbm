// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package rollback implements file staging, persistence config updates,
// data placement, and verification for Cache redis rollback.
// Process execution is orchestrated by atomredis.RedisRollback.
package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const recoverSubDir = "dbbak/recover_redis"

// doneMarkerFile records backup fingerprint for idempotency.
const doneMarkerFile = "rollback.done"

// pendingMarkerFile is written once data is in place and before startup, so a retry
// can tell a still-loading instance of this backup from a half-restored one.
const pendingMarkerFile = "rollback.pending"

const (
	loadPollInterval = 3 * time.Second
	loadLogInterval  = time.Minute
	connectTimeout   = 5 * time.Second
	minLoadDeadline  = 5 * time.Minute
	maxLoadDeadline  = 2 * time.Hour
)

// InstanceRestore one dest instance and its backup files.
type InstanceRestore struct {
	SourceIP    string
	SourcePort  int
	DestPort    int
	FullFiles   []string
	BinlogFiles []string
}

// StagedBackup holds unpacked backup files ready to be placed into data directory.
type StagedBackup struct {
	WorkDir  string
	DataFile string
	IsAOF    bool
}

// DefaultSaveDir returns the staging directory for downloaded backups.
func DefaultSaveDir() string {
	return filepath.Join(consts.GetRedisBackupDir(), recoverSubDir)
}

// Fingerprint computes a deterministic fingerprint for backup files.
func Fingerprint(files []string) string {
	names := make([]string, 0, len(files))
	for _, f := range files {
		names = append(names, filepath.Base(f))
	}
	sort.Strings(names)
	return strings.Join(names, ",")
}

// IsDone checks if the instance has already restored this exact backup.
// Verifying the fingerprint prevents skipping half-restored instances.
func IsDone(instDir, fingerprint string) bool {
	data, err := os.ReadFile(filepath.Join(instDir, doneMarkerFile))
	if err != nil {
		return false
	}
	return strings.TrimSpace(string(data)) == fingerprint
}

// MarkDone writes the completion marker after successful verification.
func MarkDone(instDir, fingerprint string) error {
	if err := os.WriteFile(filepath.Join(instDir, doneMarkerFile), []byte(fingerprint), 0644); err != nil {
		return err
	}
	_ = os.Remove(filepath.Join(instDir, pendingMarkerFile))
	return nil
}

// ClearDone removes stale markers before re-running a port.
func ClearDone(instDir string) {
	_ = os.Remove(filepath.Join(instDir, doneMarkerFile))
	_ = os.Remove(filepath.Join(instDir, pendingMarkerFile))
}

// MarkPending records that this backup's data file is in place and the instance is about to start.
func MarkPending(instDir, fingerprint string) error {
	return os.WriteFile(filepath.Join(instDir, pendingMarkerFile), []byte(fingerprint), 0644)
}

// IsPending checks if the instance was started from this exact backup but not yet verified.
func IsPending(instDir, fingerprint string) bool {
	data, err := os.ReadFile(filepath.Join(instDir, pendingMarkerFile))
	if err != nil {
		return false
	}
	return strings.TrimSpace(string(data)) == fingerprint
}

// LoadDeadline scales the loading wait with data size: 5m plus 1m per GB, capped at 2h.
func LoadDeadline(dataBytes int64) time.Duration {
	d := minLoadDeadline + time.Duration(dataBytes>>30)*time.Minute
	if d > maxLoadDeadline {
		return maxLoadDeadline
	}
	return d
}

// DataFileBytes returns the size of the persistence file placed in dataDir, or 0 if none.
func DataFileBytes(dataDir string) int64 {
	var size int64
	for _, name := range []string{"dump.rdb", "appendonly.aof"} {
		if st, err := os.Stat(filepath.Join(dataDir, name)); err == nil && st.Size() > size {
			size = st.Size()
		}
	}
	return size
}

// StageBackup unpacks full backup files and determines the persistence format.
func StageBackup(saveDir string, inst InstanceRestore) (StagedBackup, error) {
	if saveDir == "" {
		saveDir = DefaultSaveDir()
	}
	files, err := resolveFiles(saveDir, inst)
	if err != nil {
		return StagedBackup{}, err
	}
	workDir, dataFile, isAOF, err := prepareBackupFiles(saveDir, files)
	if err != nil {
		return StagedBackup{}, err
	}
	mylog.Logger.Info("staged backup for dest_port=%d: file=%s isAOF=%v", inst.DestPort, dataFile, isAOF)
	return StagedBackup{WorkDir: workDir, DataFile: dataFile, IsAOF: isAOF}, nil
}

// SetAppendonly updates appendonly in redis.conf for a specific port.
// Persistence mode is determined per port because a single host may restore both RDB and AOF backups.
func SetAppendonly(confFile string, isAOF bool) error {
	raw, err := os.ReadFile(confFile)
	if err != nil {
		return err
	}
	if err = os.WriteFile(confFile, []byte(renderAppendonly(string(raw), isAOF)), 0644); err != nil {
		return err
	}
	mylog.Logger.Info("set appendonly isAOF=%v in %s", isAOF, confFile)
	return util.LocalDirChownMysql(confFile)
}

// renderAppendonly updates or appends the active appendonly directive.
func renderAppendonly(content string, isAOF bool) string {
	value := "no"
	if isAOF {
		value = "yes"
	}
	lines := strings.Split(content, "\n")
	replaced := false
	for i, line := range lines {
		fields := strings.Fields(line)
		if len(fields) == 0 || fields[0] != "appendonly" {
			continue
		}
		lines[i] = "appendonly " + value
		replaced = true
	}
	if !replaced {
		lines = append(lines, "appendonly "+value)
	}
	return strings.Join(lines, "\n")
}

// PlaceDataFile cleans up existing dump.rdb/appendonly.aof and moves staged backup data into dataDir.
func PlaceDataFile(dataDir string, staged StagedBackup) error {
	for _, name := range []string{"dump.rdb", "appendonly.aof"} {
		stale := filepath.Join(dataDir, name)
		if !util.FileExists(stale) {
			continue
		}
		if err := os.Remove(stale); err != nil {
			return err
		}
	}
	target := filepath.Join(dataDir, "dump.rdb")
	if staged.IsAOF {
		target = filepath.Join(dataDir, "appendonly.aof")
	}
	if err := util.LocalDirChownMysql(staged.DataFile); err != nil {
		return err
	}
	if _, err := util.RunLocalCmd("bash", []string{"-c",
		fmt.Sprintf("mv -f %s %s", staged.DataFile, target)}, "", nil, 10*time.Minute); err != nil {
		return err
	}
	mylog.Logger.Info("placed %s", target)
	return util.LocalDirChownMysql(target)
}

// WaitLoaded connects to the restored instance and blocks until it has finished loading its data file.
// A reply of LOADING is not success: redis accepts connections while loading, but rejects data commands.
func WaitLoaded(addr, password string, deadline time.Duration) error {
	start := time.Now()
	var cli *myredis.RedisClient
	for {
		var err error
		cli, err = myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeRedisInstance, connectTimeout)
		if err == nil {
			break
		}
		if time.Since(start) >= deadline {
			return fmt.Errorf("rollback redis %s not reachable after %v: %v", addr, deadline, err)
		}
		time.Sleep(loadPollInterval)
	}
	defer cli.Close()

	if err := waitLoaded(cli, addr, deadline-time.Since(start), loadPollInterval); err != nil {
		return err
	}
	dbSize, err := cli.DbSize()
	if err != nil {
		return fmt.Errorf("rollback redis %s dbsize failed: %v", addr, err)
	}
	mylog.Logger.Info("%s restore from full backup success, dbsize=%d", addr, dbSize)
	return nil
}

type loadProber interface {
	Info(section string) (map[string]string, error)
}

func waitLoaded(p loadProber, addr string, deadline, interval time.Duration) error {
	end := time.Now().Add(deadline)
	var lastLog time.Time
	perc := ""
	for {
		info, err := p.Info("persistence")
		if err == nil {
			if info["loading"] == "0" {
				return nil
			}
			perc = info["loading_loaded_perc"]
		}
		if !time.Now().Before(end) {
			return fmt.Errorf("rollback redis %s still loading after %v (loaded %s%%, last err: %v)",
				addr, deadline, perc, err)
		}
		if time.Since(lastLog) >= loadLogInterval {
			mylog.Logger.Info("%s loading, loaded %s%%", addr, perc)
			lastLog = time.Now()
		}
		time.Sleep(interval)
	}
}

func resolveFiles(saveDir string, inst InstanceRestore) ([]string, error) {
	if len(inst.FullFiles) > 0 {
		var found []string
		for _, name := range inst.FullFiles {
			base := filepath.Base(name)
			p := filepath.Join(saveDir, base)
			if util.FileExists(p) {
				found = append(found, p)
				continue
			}
			matches, _ := filepath.Glob(filepath.Join(saveDir, "*"+base+"*"))
			found = append(found, matches...)
		}
		if len(found) == 0 {
			return nil, fmt.Errorf("no backup files for %s:%d in %s", inst.SourceIP, inst.SourcePort, saveDir)
		}
		return uniq(found), nil
	}
	pattern := fmt.Sprintf("*%s-%d*", inst.SourceIP, inst.SourcePort)
	matches, err := filepath.Glob(filepath.Join(saveDir, pattern))
	if err != nil || len(matches) == 0 {
		return nil, fmt.Errorf("scan backup dir %s for %s:%d failed: %v", saveDir, inst.SourceIP, inst.SourcePort, err)
	}
	return matches, nil
}

var compressedSuffixes = []string{".zst", ".gz", ".lzo", ".tar", ".tgz"}

// stageWorkDir names the per-backup unpack directory from the first (sorted) backup file.
func stageWorkDir(saveDir, first string) string {
	if strings.Contains(first, ".split.") {
		return filepath.Join(saveDir, strings.Split(first, ".split")[0])
	}
	prefix := first
	for _, ext := range compressedSuffixes {
		prefix = strings.TrimSuffix(prefix, ext)
	}
	if prefix == first {
		prefix = strings.TrimSuffix(first, filepath.Ext(first))
	}
	return filepath.Join(saveDir, prefix)
}

func runStageCmd(cmd string) error {
	_, err := util.RunLocalCmd("bash", []string{"-c", cmd}, "", nil, 1800*time.Second)
	return err
}

// prepareBackupFiles unpacks straight from the downloaded file into workDir. The download is
// never copied, and stays in place so a retry can stage it again.
func prepareBackupFiles(saveDir string, files []string) (workDir, dataFile string, isAOF bool, err error) {
	sort.Strings(files)
	first := filepath.Base(files[0])
	workDir = stageWorkDir(saveDir, first)
	if err = os.MkdirAll(workDir, 0755); err != nil {
		return
	}

	src := files[0]
	switch {
	case strings.Contains(first, ".split."):
		prefix := strings.Split(first, ".split")[0]
		err = runStageCmd(fmt.Sprintf("cd %s && cat %s.split.* | tar x -C %s", saveDir, prefix, workDir))
	case strings.HasSuffix(first, ".tar.gz") || strings.HasSuffix(first, ".tgz"):
		err = runStageCmd(fmt.Sprintf("tar -xzf %s -C %s", src, workDir))
	case strings.HasSuffix(first, ".tar"):
		err = runStageCmd(fmt.Sprintf("tar -xf %s -C %s", src, workDir))
	case strings.HasSuffix(first, ".zst"):
		if _, statErr := os.Stat(consts.ZstdBin); statErr != nil {
			return workDir, "", false, fmt.Errorf("zstd not found: %s", consts.ZstdBin)
		}
		out := filepath.Join(workDir, strings.TrimSuffix(first, ".zst"))
		err = runStageCmd(fmt.Sprintf("%s -d -f %s -o %s", consts.ZstdBin, src, out))
	case strings.HasSuffix(first, ".gz"):
		out := filepath.Join(workDir, strings.TrimSuffix(first, ".gz"))
		err = runStageCmd(fmt.Sprintf("gzip -dc %s > %s", src, out))
	case strings.HasSuffix(first, ".lzo"):
		if _, statErr := os.Stat(consts.LzopBin); statErr != nil {
			return workDir, "", false, fmt.Errorf("lzop not found: %s", consts.LzopBin)
		}
		err = runStageCmd(fmt.Sprintf("%s -d -f %s --path=%s", consts.LzopBin, src, workDir))
	default:
		// Uncompressed backup: hard link so the later mv into the data dir keeps the download.
		dst := filepath.Join(workDir, first)
		_ = os.Remove(dst)
		if linkErr := os.Link(src, dst); linkErr != nil {
			err = runStageCmd(fmt.Sprintf("cp -f %s %s", src, dst))
		}
	}
	if err != nil {
		return
	}
	dataFile, isAOF, err = pickDataFile(workDir)
	return
}

func isCompressed(name string) bool {
	for _, ext := range compressedSuffixes {
		if strings.HasSuffix(name, ext) {
			return true
		}
	}
	return false
}

func pickDataFile(workDir string) (string, bool, error) {
	entries, err := os.ReadDir(workDir)
	if err != nil {
		return "", false, err
	}
	for _, entry := range entries {
		name := entry.Name()
		if strings.Contains(name, ".aof") && !isCompressed(name) {
			return filepath.Join(workDir, name), true, nil
		}
	}
	for _, entry := range entries {
		name := entry.Name()
		if strings.Contains(name, ".rdb") && !isCompressed(name) {
			return filepath.Join(workDir, name), false, nil
		}
	}
	return "", false, fmt.Errorf("no aof/rdb found in %s", workDir)
}

// CleanupStaged removes a completed port's unpack directory and its downloaded full-backup files.
func CleanupStaged(saveDir string, inst InstanceRestore) error {
	if len(inst.FullFiles) == 0 {
		return nil
	}
	if saveDir == "" {
		saveDir = DefaultSaveDir()
	}
	files, err := resolveFiles(saveDir, inst)
	if err != nil {
		return err
	}
	sort.Strings(files)
	if err = os.RemoveAll(stageWorkDir(saveDir, filepath.Base(files[0]))); err != nil {
		return err
	}
	for _, f := range files {
		if st, statErr := os.Stat(f); statErr == nil && !st.IsDir() {
			if err = os.Remove(f); err != nil {
				return err
			}
		}
	}
	mylog.Logger.Info("cleaned staged backup for dest_port=%d", inst.DestPort)
	return nil
}

func uniq(in []string) []string {
	seen := map[string]struct{}{}
	var out []string
	for _, v := range in {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}
	return out
}
