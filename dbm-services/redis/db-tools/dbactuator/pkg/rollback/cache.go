// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"os"
	"path/filepath"
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
	loadPollInterval = 3 * time.Second
	loadLogInterval  = time.Minute
	connectTimeout   = 5 * time.Second
	minLoadDeadline  = 5 * time.Minute
	maxLoadDeadline  = 2 * time.Hour
)

// StagedBackup holds unpacked backup files ready to be placed into data directory.
type StagedBackup struct {
	WorkDir  string
	DataFile string
	IsAOF    bool
}

// cacheRestorer boots each instance once, on top of its RDB or AOF.
type cacheRestorer struct {
	Job
}

// DoRollback unpacks every backup, renders conf, places data files, starts all instances,
// then waits for each to finish loading.
func (r *cacheRestorer) DoRollback() error {
	redo, resume, err := r.resolvePending()
	if err != nil {
		return err
	}
	if len(redo) == 0 && len(resume) == 0 {
		mylog.Logger.Info("RedisRollback %s: all ports already rolled back, nothing to do", r.DestIP)
		return nil
	}
	mylog.Logger.Info("RedisRollback dest_ip=%s dest_dir=%s redo=%d resume=%d total=%d",
		r.DestIP, r.SaveDir, len(redo), len(resume), len(r.Instances))

	if len(redo) > 0 {
		// zstd and lzop live in dbtools; Prepare installs it too late for staging.
		if err = r.Host.InstallTools(); err != nil {
			mylog.Logger.Error("RedisRollback install dbtools failed: %v", err)
			return err
		}
		staged, err := r.stageBackups(redo)
		if err != nil {
			return err
		}
		if err = r.Host.Prepare(portsOf(redo)); err != nil {
			mylog.Logger.Error("RedisRollback prepare instances failed: %v", err)
			return err
		}
		if err = r.applyBackups(redo, staged); err != nil {
			return err
		}
		if err = r.startAll(redo); err != nil {
			return err
		}
	}
	return r.waitAndMark(append(redo, resume...))
}

// resolvePending splits instances into ports to restore from scratch and ports to only wait on.
// Completed ports with matching fingerprints are skipped so bamboo retries do not fail
// on in-use ports. A running port started from this same backup (pending marker) may
// still be loading, so it is resumed rather than killed. Any other running port is redone.
func (r *cacheRestorer) resolvePending() (redo, resume []InstanceRestore, err error) {
	for _, inst := range r.Instances {
		instDir := r.Host.InstanceDir(inst.DestPort)
		fingerprint := inst.Fingerprint()
		inUse, err := util.CheckPortIsInUse(r.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, nil, err
		}
		switch {
		case inUse && IsDone(instDir, fingerprint):
			mylog.Logger.Info("dest_port=%d already rolled back with the same backup, skip", inst.DestPort)
			continue
		case inUse && IsPending(instDir, fingerprint):
			mylog.Logger.Info("dest_port=%d was started from the same backup, resume waiting", inst.DestPort)
			resume = append(resume, inst)
			continue
		case inUse:
			mylog.Logger.Info("dest_port=%d is in use without a matching marker, stop it and redo", inst.DestPort)
			ClearDone(instDir)
			if err = r.Host.Stop(inst.DestPort); err != nil {
				return nil, nil, err
			}
		}
		redo = append(redo, inst)
	}
	return redo, resume, nil
}

// stageBackups unpacks full backups and identifies persistence format (AOF/RDB).
// Placeholder instances without backup files are skipped.
func (r *cacheRestorer) stageBackups(pending []InstanceRestore) (map[int]StagedBackup, error) {
	staged := make(map[int]StagedBackup, len(pending))
	var mu sync.Mutex
	err := RunBounded(len(pending), StageConcurrency(), func(i int) error {
		inst := pending[i]
		if len(inst.FullFiles) == 0 {
			mylog.Logger.Info("dest_port=%d has no full files, keep it empty", inst.DestPort)
			return nil
		}
		mylog.Logger.Info("stage source=%s:%d dest_port=%d files=%v",
			inst.SourceIP, inst.SourcePort, inst.DestPort, inst.FullFiles)
		item, err := StageBackup(r.SaveDir, inst)
		if err != nil {
			mylog.Logger.Error("RedisRollback stage %s:%d -> %d failed: %v",
				inst.SourceIP, inst.SourcePort, inst.DestPort, err)
			return err
		}
		mu.Lock()
		staged[inst.DestPort] = item
		mu.Unlock()
		return nil
	})
	if err != nil {
		return nil, err
	}
	return staged, nil
}

// applyBackups updates appendonly in redis.conf and moves staged data files into place before startup.
func (r *cacheRestorer) applyBackups(pending []InstanceRestore, staged map[int]StagedBackup) error {
	for _, inst := range pending {
		instDir := r.Host.InstanceDir(inst.DestPort)
		// Placeholder instances have nothing staged and keep default persistence from dbconfig.
		if item, ok := staged[inst.DestPort]; ok {
			if err := SetAppendonly(filepath.Join(instDir, "redis.conf"), item.IsAOF); err != nil {
				mylog.Logger.Error("RedisRollback set appendonly for %d failed: %v", inst.DestPort, err)
				return err
			}
			if err := PlaceDataFile(filepath.Join(instDir, "data"), item); err != nil {
				mylog.Logger.Error("RedisRollback place data file for %d failed: %v", inst.DestPort, err)
				return err
			}
		}
		if err := MarkPending(instDir, inst.Fingerprint()); err != nil {
			return err
		}
	}
	return nil
}

// startAll starts every instance before waiting, so large data files load in parallel.
func (r *cacheRestorer) startAll(pending []InstanceRestore) error {
	for _, inst := range pending {
		if err := r.Host.Start(inst.DestPort); err != nil {
			mylog.Logger.Error("RedisRollback start %s:%d failed: %v", r.DestIP, inst.DestPort, err)
			return err
		}
	}
	return nil
}

// waitAndMark waits for every instance to finish loading, marks each one done as it succeeds
// and frees its staged files. Failed ports keep their downloads for the next retry.
func (r *cacheRestorer) waitAndMark(pending []InstanceRestore) error {
	return RunBounded(len(pending), len(pending), func(i int) error {
		inst := pending[i]
		instDir := r.Host.InstanceDir(inst.DestPort)
		addr := fmt.Sprintf("%s:%d", r.DestIP, inst.DestPort)
		password, err := myredis.GetRedisPasswdFromConfFile(inst.DestPort)
		if err != nil {
			return err
		}
		deadline := LoadDeadline(DataFileBytes(filepath.Join(instDir, "data")))
		if err = WaitLoaded(addr, password, deadline); err != nil {
			mylog.Logger.Error("RedisRollback %s: %v", addr, err)
			return err
		}
		if err = MarkDone(instDir, inst.Fingerprint()); err != nil {
			return err
		}
		if err = CleanupStaged(r.SaveDir, inst); err != nil {
			mylog.Logger.Warn("RedisRollback cleanup staged files for %d failed: %v", inst.DestPort, err)
		}
		return nil
	})
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
	workDir, err := unpackBackup(saveDir, files)
	if err != nil {
		return StagedBackup{}, err
	}
	dataFile, isAOF, err := pickDataFile(workDir)
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
	cli, err := connectWithin(addr, password, consts.TendisTypeRedisInstance, deadline)
	if err != nil {
		return err
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

// connectWithin retries connecting until deadline; a freshly started instance may not listen yet.
func connectWithin(addr, password, dbType string, deadline time.Duration) (*myredis.RedisClient, error) {
	start := time.Now()
	for {
		cli, err := myredis.NewRedisClientWithRetry(addr, password, 0, dbType, connectTimeout)
		if err == nil {
			return cli, nil
		}
		if time.Since(start) >= deadline {
			return nil, fmt.Errorf("rollback redis %s not reachable after %v: %v", addr, deadline, err)
		}
		time.Sleep(loadPollInterval)
	}
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
