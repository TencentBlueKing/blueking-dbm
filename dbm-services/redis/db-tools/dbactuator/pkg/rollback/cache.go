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
	// AOF loading replays every command, about ten times slower than reading an RDB.
	aofLoadFactor      = 10
	maxAOFLoadDeadline = 12 * time.Hour
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

// errCollector keeps the first error of concurrent ports.
type errCollector struct {
	mu  sync.Mutex
	err error
}

func (c *errCollector) add(err error) {
	if err == nil {
		return
	}
	c.mu.Lock()
	if c.err == nil {
		c.err = err
	}
	c.mu.Unlock()
}

// DoRollback runs every port on its own: unpack, place the data file, start once memory allows,
// wait for the load. A port starts as soon as it is unpacked and fits; none waits for a batch.
func (r *cacheRestorer) DoRollback() error {
	limits := HostLimits(r.MaxConcurrency)
	report := newHostReport(r.DestIP, "cache", r.Instances)
	defer report.logResult()

	redo, resume, err := r.resolvePending(report)
	if err != nil {
		return err
	}
	if len(redo) == 0 && len(resume) == 0 {
		mylog.Logger.Info("RedisRollback %s: all ports already rolled back, nothing to do", r.DestIP)
		return nil
	}
	report.logPlan(limits, r.portPlans(append(append([]InstanceRestore{}, redo...), resume...)), r.UnpackDir)

	window := newMemWindow(limits.MemAvailable, limits.Loading())
	var wg sync.WaitGroup
	var errs errCollector
	for _, inst := range resume {
		dataDir := filepath.Join(r.Host.InstanceDir(inst.DestPort), "data")
		need := CacheMemory(DataFileBytes(dataDir), isAOFData(dataDir))
		window.admit(need)
		wg.Add(1)
		go func(inst InstanceRestore) {
			defer wg.Done()
			errs.add(r.waitAndMark(inst, need, window, report.port(inst.DestPort)))
		}(inst)
	}

	if len(redo) > 0 {
		// zstd and lzop live in dbtools; Prepare installs it too late for unpacking.
		if err = r.Host.InstallTools(); err != nil {
			mylog.Logger.Error("RedisRollback install dbtools failed: %v", err)
			wg.Wait()
			return err
		}
		if err = r.Host.Prepare(portsOf(redo)); err != nil {
			mylog.Logger.Error("RedisRollback prepare instances failed: %v", err)
			wg.Wait()
			return err
		}
		errs.add(RunBounded(len(redo), limits.Unpack, func(i int) error {
			inst := redo[i]
			p := report.port(inst.DestPort)
			need, err := r.stage(inst, p)
			if err != nil {
				p.finish(err)
				return err
			}
			// Hand the port over so this unpack slot moves on while it waits for memory.
			wg.Add(1)
			go func() {
				defer wg.Done()
				errs.add(r.startAndWait(inst, need, window, p))
			}()
			return nil
		}))
	}
	wg.Wait()
	return errs.err
}

func (r *cacheRestorer) portPlans(instances []InstanceRestore) map[int]portPlan {
	plans := make(map[int]portPlan, len(instances))
	for _, inst := range instances {
		var full, memory int64
		for _, name := range inst.FullFiles {
			size := totalSize([]string{filepath.Join(r.SaveDir, filepath.Base(name))})
			full += size
			if isCompressed(name) {
				size *= 3
			}
			memory += CacheMemory(size, strings.Contains(name, ".aof"))
		}
		plans[inst.DestPort] = portPlan{fullBytes: full, memory: memory}
	}
	return plans
}

// resolvePending splits instances into ports to restore from scratch and ports to only wait on.
// Completed ports with matching fingerprints are skipped so bamboo retries do not fail
// on in-use ports. A running port started from this same backup (pending marker) may
// still be loading, so it is resumed rather than killed. Any other running port is redone.
func (r *cacheRestorer) resolvePending(report *hostReport) (redo, resume []InstanceRestore, err error) {
	for _, inst := range r.Instances {
		instDir := r.Host.InstanceDir(inst.DestPort)
		fingerprint := inst.Fingerprint()
		log := newPortLog(r.DestIP, inst)
		inUse, err := util.CheckPortIsInUse(r.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, nil, err
		}
		switch {
		case inUse && IsDone(instDir, fingerprint):
			log.Info("already rolled back with the same backup, skip")
			report.skipped(inst.DestPort)
			continue
		case inUse && IsPending(instDir, fingerprint):
			log.Info("was started from the same backup, resume waiting")
			resume = append(resume, inst)
			continue
		case inUse:
			log.Info("in use without a matching marker, stop it and redo")
			ClearDone(instDir)
			if err = r.Host.Stop(inst.DestPort); err != nil {
				return nil, nil, err
			}
		}
		redo = append(redo, inst)
	}
	return redo, resume, nil
}

// stage unpacks inst's backup onto the data disk and puts it in place, returning the memory the
// instance will take. Placeholders without backup files start empty.
func (r *cacheRestorer) stage(inst InstanceRestore, p *portReport) (int64, error) {
	log := newPortLog(r.DestIP, inst)
	instDir := r.Host.InstanceDir(inst.DestPort)
	var need int64
	if len(inst.FullFiles) > 0 {
		log.Info("unpack files=%v into %s", inst.FullFiles, r.portWorkDir(inst.DestPort))
		var item StagedBackup
		err := p.timed(stageUnpack, func() (err error) {
			if files, ferr := resolveFiles(r.SaveDir, inst); ferr == nil {
				p.add(stageDownload, downloadSpan(files))
			}
			item, err = StageBackup(r.SaveDir, r.portWorkDir(inst.DestPort), inst)
			return err
		})
		if err != nil {
			log.Error("unpack failed: %v", err)
			return 0, err
		}
		if st, err := os.Stat(item.DataFile); err == nil {
			need = CacheMemory(st.Size(), item.IsAOF)
		}
		err = p.timed(stageRestore, func() error {
			if err := SetPersistence(confFile(instDir), item.IsAOF); err != nil {
				return err
			}
			return PlaceDataFile(log, filepath.Join(instDir, "data"), item)
		})
		if err != nil {
			log.Error("place data file failed: %v", err)
			return 0, err
		}
	} else {
		log.Info("no full files, keep it empty")
	}
	return need, MarkPending(instDir, inst.Fingerprint())
}

// startAndWait starts inst once its memory fits, then waits for the load.
func (r *cacheRestorer) startAndWait(inst InstanceRestore, need int64, window *memWindow, p *portReport) error {
	log := newPortLog(r.DestIP, inst)
	if err := window.acquire(need); err != nil {
		err = fmt.Errorf("start %s:%d: %v", r.DestIP, inst.DestPort, err)
		log.Error("%v", err)
		p.finish(err)
		return err
	}
	log.Info("start, memory~%s", humanBytes(need))
	if err := p.timed(stageStart, func() error { return r.Host.Start(inst.DestPort) }); err != nil {
		window.release(need)
		log.Error("start failed: %v", err)
		p.finish(err)
		return err
	}
	return r.waitAndMark(inst, need, window, p)
}

// waitAndMark waits for inst to finish loading, marks it done and frees its staged files.
// A failed port keeps its downloads for the next retry.
func (r *cacheRestorer) waitAndMark(inst InstanceRestore, need int64, window *memWindow, p *portReport) error {
	log := newPortLog(r.DestIP, inst)
	err := r.waitLoaded(inst, log, p, window, need)
	if err == nil {
		err = MarkDone(r.Host.InstanceDir(inst.DestPort), inst.Fingerprint())
	}
	if err != nil {
		log.Error("%v", err)
		p.finish(err)
		return err
	}
	if err = CleanupStaged(r.SaveDir, r.portWorkDir(inst.DestPort), inst); err != nil {
		log.Warn("cleanup staged files failed: %v", err)
	}
	p.finish(nil)
	return nil
}

func (r *cacheRestorer) waitLoaded(inst InstanceRestore, log portLog, p *portReport, window *memWindow,
	need int64) error {
	start := time.Now()
	defer func() { p.add(stageStart, time.Since(start)) }()
	instDir := r.Host.InstanceDir(inst.DestPort)
	password, err := myredis.GetRedisPasswdFromConfFile(inst.DestPort)
	if err != nil {
		window.release(need)
		return err
	}
	dataDir := filepath.Join(instDir, "data")
	addr := fmt.Sprintf("%s:%d", r.DestIP, inst.DestPort)
	rss, err := WaitLoaded(log, addr, password, LoadDeadline(DataFileBytes(dataDir), isAOFData(dataDir)))
	if err != nil {
		window.release(need)
		return err
	}
	window.loaded(need, rss)
	return nil
}

// LoadDeadline scales the loading wait with data size: 5m plus 1m per GB, capped at 2h, and ten
// times as long per GB for an AOF.
func LoadDeadline(dataBytes int64, isAOF bool) time.Duration {
	perGB, ceiling := time.Minute, maxLoadDeadline
	if isAOF {
		perGB, ceiling = aofLoadFactor*time.Minute, maxAOFLoadDeadline
	}
	d := minLoadDeadline + time.Duration(dataBytes>>30)*perGB
	if d > ceiling {
		return ceiling
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

func isAOFData(dataDir string) bool {
	return util.FileExists(filepath.Join(dataDir, "appendonly.aof"))
}

// StageBackup unpacks inst's full backup into workDir and determines the persistence format.
func StageBackup(saveDir, workDir string, inst InstanceRestore) (StagedBackup, error) {
	if saveDir == "" {
		saveDir = DefaultSaveDir()
	}
	files, err := resolveFiles(saveDir, inst)
	if err != nil {
		return StagedBackup{}, err
	}
	if err = unpackBackup(files, workDir); err != nil {
		return StagedBackup{}, err
	}
	dataFile, isAOF, err := pickDataFile(workDir)
	if err != nil {
		return StagedBackup{}, err
	}
	return StagedBackup{WorkDir: workDir, DataFile: dataFile, IsAOF: isAOF}, nil
}

// SetPersistence writes the port's persistence into redis.conf before its only start: appendonly
// follows the backup format, decided per port as a host may restore both RDB and AOF backups,
// and save is off so finishing the load does not fork a bgsave that doubles memory.
func SetPersistence(confFile string, isAOF bool) error {
	raw, err := os.ReadFile(confFile)
	if err != nil {
		return err
	}
	content := renderAppendonly(string(raw), isAOF)
	content = renderDirective(content, "save", `""`)
	if err = os.WriteFile(confFile, []byte(content), 0644); err != nil {
		return err
	}
	return util.LocalDirChownMysql(confFile)
}

// renderAppendonly updates or appends the active appendonly directive.
func renderAppendonly(content string, isAOF bool) string {
	value := "no"
	if isAOF {
		value = "yes"
	}
	return renderDirective(content, "appendonly", value)
}

// renderDirective replaces every active line of a directive with one value, or appends it.
func renderDirective(content, name, value string) string {
	lines := strings.Split(content, "\n")
	out := lines[:0]
	replaced := false
	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) == 0 || fields[0] != name {
			out = append(out, line)
			continue
		}
		if !replaced {
			out = append(out, name+" "+value)
			replaced = true
		}
	}
	if !replaced {
		out = append(out, name+" "+value)
	}
	return strings.Join(out, "\n")
}

// PlaceDataFile cleans up existing dump.rdb/appendonly.aof and moves staged backup data into dataDir.
func PlaceDataFile(log portLog, dataDir string, staged StagedBackup) error {
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
	if err := placeFile(log, staged.DataFile, target); err != nil {
		return err
	}
	log.Info("placed %s", target)
	return util.LocalDirChownMysql(target)
}

// WaitLoaded connects to the restored instance and blocks until it has finished loading its data
// file, returning its resident memory when known. Redis accepts connections while loading but
// rejects data commands, so LOADING is not success.
func WaitLoaded(log portLog, addr, password string, deadline time.Duration) (int64, error) {
	start := time.Now()
	cli, err := connectWithin(addr, password, consts.TendisTypeRedisInstance, deadline)
	if err != nil {
		return 0, err
	}
	defer cli.Close()

	if err := waitLoaded(cli, log, addr, deadline-time.Since(start), loadPollInterval); err != nil {
		return 0, err
	}
	dbSize, err := cli.DbSize()
	if err != nil {
		return 0, fmt.Errorf("rollback redis %s dbsize failed: %v", addr, err)
	}
	var rss int64
	if info, err := cli.Info("memory"); err == nil {
		rss, _ = strconv.ParseInt(info["used_memory_rss"], 10, 64)
	}
	log.Info("restore from full backup success, dbsize=%d rss=%s", dbSize, humanBytes(rss))
	return rss, nil
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

func waitLoaded(p loadProber, log portLog, addr string, deadline, interval time.Duration) error {
	end := time.Now().Add(deadline)
	var lastLog time.Time
	perc, eta := "", ""
	for {
		info, err := p.Info("persistence")
		if err == nil {
			if info["loading"] == "0" {
				return nil
			}
			perc, eta = info["loading_loaded_perc"], info["loading_eta_seconds"]
		}
		if !time.Now().Before(end) {
			return fmt.Errorf("rollback redis %s still loading after %v (loaded %s%%, last err: %v)",
				addr, deadline, perc, err)
		}
		if time.Since(lastLog) >= loadLogInterval {
			log.Info("loading, loaded %s%%, eta %ss", perc, eta)
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
