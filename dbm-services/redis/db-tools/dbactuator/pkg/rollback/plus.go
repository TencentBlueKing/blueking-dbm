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
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-redis/redis/v8"
)

const (
	// restorebackup blocks until every kvstore is copied or moved into place.
	plusRestoreTimeout = 6 * time.Hour
	plusCommandTimeout = 10 * time.Minute
	plusToolTimeout    = 2 * time.Hour
	restoreBinlogCmd   = "restorebinlogv2"
	// A ReplLogKeyV2 is a RecordKey whose primary key is the binlog id as 8 big-endian bytes, after
	// a 4-byte chunk id, a type byte and a 4-byte db id.
	binlogIDOffset = 4 + 1 + 4
)

var (
	// binlog-{ip}-{port}-{kvstore}-{index}-{yyyymmddHHMMSS}.log.zst
	plusBinlogReg = regexp.MustCompile(`^binlog-(?:(\d{1,3}(?:\.\d{1,3}){3})-)?(\d+)-(\d+)-(\d+)-\d{14}\.log\.(?:zst|lzo)$`)
	plusMediaReg  = regexp.MustCompile(`(?i)tendisplus-(\d+)\.`)
)

// plusRestorer restores Tendisplus online: restorebackup into a running instance that is still
// alone, then every kvstore replays its binlogs through restorebinlogv2, which keeps the original
// binlog ids, so binlogpos afterwards proves the planned writes all went in. A cluster instance
// takes its slots last, and FormCluster joins the instances once every port is done.
type plusRestorer struct {
	Job
	cluster bool
}

type plusBackupMeta struct {
	BinlogPos     uint64 `json:"binlogpos"`
	BinlogVersion int    `json:"binlogVersion"`
}

// DoRollback checks every planned binlog chain on disk before touching an instance. A port whose
// full backup is already in place from an earlier attempt resumes its replay; the others restore,
// up to the unpack limit at a time, and start replaying as soon as they are restored.
func (r *plusRestorer) DoRollback() error {
	recoverAt, err := time.Parse(time.RFC3339, r.RecoverAt)
	if err != nil {
		return fmt.Errorf("invalid recover_at %q: %v", r.RecoverAt, err)
	}
	limits := HostLimits(r.MaxConcurrency)
	report := r.newReport(enginePlus)
	defer report.logResult()

	redo, resume, err := r.resolvePending(report)
	if err != nil {
		return err
	}
	if len(redo) == 0 && len(resume) == 0 {
		logInfo("RedisRollback: all ports already rolled back")
		return nil
	}

	all := append(append([]InstanceRestore{}, redo...), resume...)
	chains := make(map[int]map[int][]string, len(all))
	plans := make(map[int]portPlan, len(all))
	streams := 0
	for _, inst := range all {
		var gaps map[int][]int64
		chains[inst.DestPort], gaps, err = LocalKvstoreBinlogs(r.SaveDir, inst, r.AllowBinlogNonconsecutive)
		if err != nil {
			report.port(inst.DestPort).finish(err)
			return err
		}
		gapped := make([]int, 0, len(gaps))
		for kvstore := range gaps {
			gapped = append(gapped, kvstore)
		}
		sort.Ints(gapped)
		for _, kvstore := range gapped {
			report.port(inst.DestPort).allowedGaps(fmt.Sprintf("kv%d ", kvstore), gaps[kvstore])
			newPortLog(inst.DestPort).Warn("kv%d binlogs skip %s, as the plan allows: the temp instance "+
				"misses their writes", kvstore, indexRanges(gaps[kvstore]))
		}
		var binlogs, full []string
		for _, chain := range chains[inst.DestPort] {
			binlogs = append(binlogs, chain...)
		}
		for _, name := range inst.FullFiles {
			full = append(full, filepath.Join(r.SaveDir, filepath.Base(name)))
		}
		streams += len(chains[inst.DestPort])
		plans[inst.DestPort] = portPlan{fullBytes: totalSize(full), binlogs: len(binlogs),
			binlogBytes: totalSize(binlogs)}
	}

	if err = r.Host.InstallTools(); err != nil {
		return err
	}
	if len(redo) > 0 {
		if err = r.Host.Prepare(portsOf(redo)); err != nil {
			return err
		}
		if err = r.setClusterConf(redo); err != nil {
			return err
		}
		if err = r.applyTuning(portsOf(redo)); err != nil {
			return err
		}
	}
	// A resumed port was tuned by the attempt that restored it; memory is read from its conf as is.
	report.tuning = r.tuningSummary()
	for _, inst := range all {
		plan := plans[inst.DestPort]
		plan.memory = PlusMemory(confFile(r.Host.InstanceDir(inst.DestPort)))
		plans[inst.DestPort] = plan
	}
	replaying := limits.KvstoreReplay(streams)
	report.logPlan(limits, plans, r.UnpackDir, fmt.Sprintf("%d of %d kvstores at once", replaying, streams))
	defer report.trackProgress()()

	window := newMemWindow(limits.MemAvailable, len(all))
	replaySlots := make(chan struct{}, replaying)
	var wg sync.WaitGroup
	var errs errCollector
	replayLater := func(inst InstanceRestore, p *portReport) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			errs.add(r.replayAndMark(inst, p, chains[inst.DestPort], recoverAt, replaySlots))
		}()
	}
	for _, inst := range resume {
		// Already running: its caches are resident whether or not they fit.
		_ = window.reserve(plans[inst.DestPort].memory)
		replayLater(inst, report.port(inst.DestPort))
	}
	errs.add(RunBounded(len(redo), limits.Unpack, func(i int) error {
		inst := redo[i]
		p := report.port(inst.DestPort)
		if err := r.restore(inst, p, window); err != nil {
			p.finish(err)
			return err
		}
		replayLater(inst, p)
		return nil
	}))
	wg.Wait()
	return errs.err
}

// setClusterConf writes the cluster directives of a cluster instance; others keep their conf.
func (r *plusRestorer) setClusterConf(instances []InstanceRestore) error {
	if !r.cluster {
		return nil
	}
	for _, inst := range instances {
		if err := SetClusterConf(confFile(r.Host.InstanceDir(inst.DestPort))); err != nil {
			return err
		}
	}
	return nil
}

func (r *plusRestorer) fingerprint(inst InstanceRestore) string {
	return inst.Fingerprint() + "|" + r.RecoverAt
}

// resolvePending skips ports already rolled back to the same point and resumes the replay of ports
// whose full backup was restored by an earlier attempt; any other running port is redone.
func (r *plusRestorer) resolvePending(report *hostReport) (redo, resume []InstanceRestore, err error) {
	for _, inst := range r.Instances {
		instDir := r.Host.InstanceDir(inst.DestPort)
		fingerprint := r.fingerprint(inst)
		log := newPortLog(inst.DestPort)
		inUse, err := util.CheckPortIsInUse(r.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, nil, err
		}
		switch {
		case inUse && IsDone(instDir, fingerprint):
			log.Info("skip: already rolled back to this point")
			report.skipped(inst.DestPort)
			continue
		case inUse && IsPending(instDir, fingerprint):
			log.Info("resume: full backup restored, replay on")
			resume = append(resume, inst)
			continue
		case inUse:
			log.Info("redo: in use without a matching marker")
			if err = r.Host.Stop(inst.DestPort); err != nil {
				return nil, nil, err
			}
		}
		ClearDone(instDir)
		redo = append(redo, inst)
	}
	return redo, resume, nil
}

// restore unpacks inst's full backup onto the data disk, starts the instance empty and has it
// restorebackup the unpacked copy. Placeholders start empty and stay so.
func (r *plusRestorer) restore(inst InstanceRestore, p *portReport, window *memWindow) error {
	log := newPortLog(inst.DestPort)
	instDir := r.Host.InstanceDir(inst.DestPort)
	workDir := r.portWorkDir(inst.DestPort)
	var root string
	var metas map[int]plusBackupMeta
	if len(inst.FullFiles) > 0 {
		var size int64
		err := p.timed(stageUnpack, func() error {
			files, err := resolveFiles(r.SaveDir, inst)
			if err != nil {
				return err
			}
			size = totalSize(files)
			cpu, err := unpackPort(p, files, workDir)
			p.addCPU(stageUnpack, cpu)
			if err != nil {
				return err
			}
			if root, err = plusBackupRoot(workDir); err != nil {
				return err
			}
			if metas, err = readPlusBackupMetas(root); err != nil {
				return err
			}
			// tendisplus runs as mysql and moves the kvstores out of the unpacked copy.
			return util.LocalDirChownMysql(workDir)
		})
		if err != nil {
			log.Error("unpack failed: %v", err)
			return err
		}
		log.Info("unpacked %s in %s", shortBytes(size), shortDuration(p.duration(stageUnpack)))
	}
	need := PlusMemory(confFile(instDir))
	if err := window.reserve(need); err != nil {
		err = fmt.Errorf("start %s:%d: %v", r.DestIP, inst.DestPort, err)
		log.Error("%v", err)
		return err
	}
	p.enter(phaseStart, 0, "")
	if err := p.timed(stageStart, func() error { return r.Host.Start(inst.DestPort) }); err != nil {
		window.unreserve(need)
		log.Error("start failed: %v", err)
		return err
	}
	log.Info("started, memory~%s", shortBytes(need))
	if len(inst.FullFiles) == 0 {
		log.Info("no full files, left empty")
		return MarkPending(instDir, r.fingerprint(inst))
	}
	p.enter(phaseRestore, 0, "")
	err := r.timedOnInstance(log, p, inst.DestPort, stageRestore, func() error {
		return r.restoreBackup(log, p, inst, instDir, root, metas)
	})
	if err != nil {
		log.Error("restore failed: %v", err)
		p.detail("ERROR restore: %v", err)
		return err
	}
	log.Info("restored (%s) in %s", p.restoredHow(), shortDuration(p.duration(stageRestore)))
	if err = os.RemoveAll(workDir); err != nil {
		log.Warn("remove unpacked backup %s failed: %v", workDir, err)
	}
	return MarkPending(instDir, r.fingerprint(inst))
}

func (r *plusRestorer) restoreBackup(log portLog, p *portReport, inst InstanceRestore, instDir, root string,
	metas map[int]plusBackupMeta) error {
	addr := fmt.Sprintf("%s:%d", r.DestIP, inst.DestPort)
	password, err := portPassword(inst.DestPort)
	if err != nil {
		return err
	}
	cli, err := myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeTendisplusInsance,
		plusRestoreTimeout)
	if err != nil {
		return err
	}
	defer cli.Close()
	kvstores, err := cli.GetKvstoreCount()
	if err != nil {
		return err
	}
	if err = checkPlusBackup(inst, metas, kvstores, r.Host.MediaName()); err != nil {
		return err
	}

	// A backup taken as a checkpoint is renamed into place when asked; one taken as a copy, as dbmon
	// takes them across top-level dirs, is always copied. The backup is never rewritten to change that.
	dbDir := confDir(instDir, filepath.Join(instDir, "data", "db"))
	same, derr := sameDeviceFn(root, dbDir)
	switch {
	case derr != nil:
		log.Warn("restorebackup copies: cannot compare filesystems of %s and %s: %v", root, dbDir, derr)
	case !same:
		log.Warn("restorebackup copies: %s and %s are on different filesystems", root, dbDir)
	default:
		if _, err = cli.ConfigSet("move-dir-when-restore-ckpt", "yes"); err != nil {
			log.Warn("restorebackup copies: set move-dir-when-restore-ckpt failed: %v", err)
		}
	}
	if err = cli.InstanceClient.Do(context.TODO(), "restorebackup", "all", root, "force").Err(); err != nil {
		return fmt.Errorf("restorebackup all %s failed: %v", root, err)
	}
	p.setRestored(restoredHow(root, len(metas)))
	// Each kvstore restarts at the binlogpos of its backup, and the replay goes on from there.
	replayer := redisReplayer{cli: cli}
	for kvstore := 0; kvstore < len(metas); kvstore++ {
		pos, err := replayer.BinlogPos(kvstore)
		if err != nil {
			return err
		}
		if pos < metas[kvstore].BinlogPos {
			return fmt.Errorf("kvstore %d binlogpos %d after restorebackup is behind its backup's %d",
				kvstore, pos, metas[kvstore].BinlogPos)
		}
	}
	return nil
}

// Ways restorebackup placed a backup, as seen from the unpacked copy afterwards.
const (
	restoredMoved  = "moved"
	restoredCopied = "copied"
)

// restoredHow tells a moved backup, whose kvstore dirs are gone from root, from a copied one.
func restoredHow(root string, kvstores int) string {
	for kvstore := 0; kvstore < kvstores; kvstore++ {
		if util.FileExists(filepath.Join(root, strconv.Itoa(kvstore))) {
			return restoredCopied
		}
	}
	return restoredMoved
}

// checkPlusBackup is the gate before restorebackup: the temp instance must have as many kvstores as
// the source, each with a planned binlog chain when there are any, and its media must read the
// backup's binlog version.
func checkPlusBackup(inst InstanceRestore, metas map[int]plusBackupMeta, kvstoreCount, media string) error {
	kvstores, err := strconv.Atoi(strings.TrimSpace(kvstoreCount))
	if err != nil {
		return fmt.Errorf("invalid kvstorecount %q of the temp instance", kvstoreCount)
	}
	if kvstores != len(metas) {
		return fmt.Errorf("backup holds %d kvstores but the temp instance has %d; they must be equal",
			len(metas), kvstores)
	}
	if len(inst.KvstoreBinlogs) > 0 && len(inst.KvstoreBinlogs) != len(metas) {
		return fmt.Errorf("backup holds %d kvstores but %d binlog chains are planned", len(metas),
			len(inst.KvstoreBinlogs))
	}
	supported := mediaBinlogVersion(media)
	if supported == 0 {
		return nil
	}
	for kvstore := 0; kvstore < len(metas); kvstore++ {
		if v := metas[kvstore].BinlogVersion; v > supported {
			return fmt.Errorf("kvstore %d backup has binlog version %d, newer than %s reads (%d)",
				kvstore, v, media, supported)
		}
	}
	return nil
}

// mediaBinlogVersion is the binlog version a Tendisplus media writes and reads: 2 since 2.0, 0 when
// the media name does not tell.
func mediaBinlogVersion(media string) int {
	m := plusMediaReg.FindStringSubmatch(media)
	if m == nil {
		return 0
	}
	if major, _ := strconv.Atoi(m[1]); major >= 2 {
		return 2
	}
	return 1
}

// plusBackupRoot locates the backup inside workDir: the tar holds one directory named after the
// backup, with one sub directory per kvstore.
func plusBackupRoot(workDir string) (string, error) {
	isRoot := func(dir string) bool { return util.FileExists(filepath.Join(dir, "0", "backup_meta")) }
	if isRoot(workDir) {
		return workDir, nil
	}
	entries, err := os.ReadDir(workDir)
	if err != nil {
		return "", err
	}
	if len(entries) == 1 && entries[0].IsDir() && isRoot(filepath.Join(workDir, entries[0].Name())) {
		return filepath.Join(workDir, entries[0].Name()), nil
	}
	return "", fmt.Errorf("no tendisplus backup (0/backup_meta) found in %s", workDir)
}

// readPlusBackupMetas reads backup_meta of every kvstore directory; they must be numbered 0..n-1.
func readPlusBackupMetas(root string) (map[int]plusBackupMeta, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	metas := map[int]plusBackupMeta{}
	for _, e := range entries {
		kvstore, err := strconv.Atoi(e.Name())
		if err != nil || !e.IsDir() {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(root, e.Name(), "backup_meta"))
		if err != nil {
			return nil, fmt.Errorf("kvstore %d of backup %s: %v", kvstore, root, err)
		}
		var meta plusBackupMeta
		if err = json.Unmarshal(raw, &meta); err != nil {
			return nil, fmt.Errorf("kvstore %d backup_meta of %s: %v", kvstore, root, err)
		}
		metas[kvstore] = meta
	}
	for kvstore := 0; kvstore < len(metas); kvstore++ {
		if _, ok := metas[kvstore]; !ok {
			return nil, fmt.Errorf("kvstores of backup %s are not numbered 0..%d", root, len(metas)-1)
		}
	}
	if len(metas) == 0 {
		return nil, fmt.Errorf("no kvstore in backup %s", root)
	}
	return metas, nil
}

// replayAndMark replays inst's binlogs, takes its planned slots on a cluster, then marks it done and
// frees its downloads. Slots come after the replay so that the instance owns nothing while data goes in.
func (r *plusRestorer) replayAndMark(inst InstanceRestore, p *portReport, chains map[int][]string,
	recoverAt time.Time, slots chan struct{}) error {
	log := newPortLog(inst.DestPort)
	sample := r.sampleInstanceCPU(log, inst.DestPort, len(chains) > 0)
	err := r.replay(log, p, inst, chains, recoverAt, slots)
	sample(p)
	if failedInFlight(err) {
		// binlogpos may be past the failed binlog, so resuming from it would skip that write.
		ClearDone(r.Host.InstanceDir(inst.DestPort))
		log.Warn("replay failed with a batch out, a retry restores the full backup again")
	}
	if err == nil && r.cluster {
		if err = assignPortSlotsFn(log, r.DestIP, inst); err == nil {
			// After addslots, the instance knows which slots it keeps and drops the restored
			// chunks of any other slot.
			err = restoreEndFn(log, r.DestIP, inst)
		}
	}
	if err == nil && (len(inst.FullFiles) > 0 || len(chains) > 0) {
		r.checkHeartbeat(log, p, inst, chains, recoverAt)
	}
	if err == nil {
		err = MarkDone(r.Host.InstanceDir(inst.DestPort), r.fingerprint(inst))
	}
	if err != nil {
		log.Error("failed: %v", err)
		p.finish(err)
		return err
	}
	if err = CleanupStaged(r.SaveDir, r.portWorkDir(inst.DestPort), inst); err != nil {
		log.Warn("cleanup staged files failed: %v", err)
	}
	for _, chain := range chains {
		for _, f := range chain {
			_ = os.Remove(f)
		}
	}
	p.finish(nil)
	log.Info("done")
	return nil
}

// checkHeartbeat compares the source heartbeat each kvstore holds with recoverAt, as v1 does.
// dbmon writes it to every kvstore of the source, so once the restore reaches recoverAt it should
// be within the tolerance of it. A quiet source or a paused dbmon leaves it stale even when every
// planned binlog went in, so a heartbeat out of the tolerance, or one that cannot be read, is a
// warning on the port and never fails it. A source that wrote none, or a replayed kvstore without
// one, is logged and not checked.
func (r *plusRestorer) checkHeartbeat(log portLog, p *portReport, inst InstanceRestore, chains map[int][]string,
	recoverAt time.Time) {
	key := fmt.Sprintf("%s_%d:heartbeat", inst.SourceIP, inst.SourcePort)
	cli, closeFn, err := dialPlusFn(r.DestIP, inst.DestPort)
	if err != nil {
		p.heartbeatOff(log, "heartbeat %s not read: %v", key, err)
		return
	}
	defer closeFn()
	beats, err := cli.Heartbeat(key)
	if err != nil {
		p.heartbeatOff(log, "heartbeat %s not read: %v", key, err)
		return
	}
	if len(beats) == 0 {
		log.Info("no heartbeat under %s, heartbeat check skipped", key)
		return
	}
	tolerance := r.heartbeatTolerance()
	seen := map[int]bool{}
	for kvstore := range chains {
		seen[kvstore] = true
	}
	for kvstore := range beats {
		seen[kvstore] = true
	}
	kvstores := make([]int, 0, len(seen))
	for kvstore := range seen {
		kvstores = append(kvstores, kvstore)
	}
	sort.Ints(kvstores)
	var off []string
	var missing []int
	for _, kvstore := range kvstores {
		beat, ok := beats[kvstore]
		if !ok {
			missing = append(missing, kvstore)
			continue
		}
		p.kvstoreHeartbeat(kvstore, beat)
		if beatOff(beat, recoverAt, tolerance) {
			off = append(off, fmt.Sprintf("kvstore %d at %s", kvstore, beat.Local().Format(time.RFC3339)))
		}
	}
	if len(missing) > 0 {
		log.Warn("kvstores %v hold no heartbeat under %s, not checked", missing, key)
	}
	if len(off) > 0 {
		p.heartbeatOff(log, "heartbeat %s is more than %s from recover_at %s: %s", key, tolerance,
			recoverAt.Local().Format(time.RFC3339), strings.Join(off, ", "))
		return
	}
	log.Info("heartbeat of %d kvstores within %s of recover_at", len(kvstores)-len(missing), tolerance)
}

// instanceCPUSince reads the instance's CPU now and returns what reads its use since. ok is false
// when the process cannot be read or was restarted in between, which is logged and fails nothing.
func (j Job) instanceCPUSince(log portLog, port int) func() (d time.Duration, ok bool) {
	pid, start, err := j.Host.ProcessID(port)
	var before time.Duration
	if err == nil {
		before, err = processCPU(pid, start)
	}
	if err != nil {
		log.Warn("instance cpu not sampled: %v", err)
		return func() (time.Duration, bool) { return 0, false }
	}
	return func() (time.Duration, bool) {
		after, err := processCPU(pid, start)
		if err != nil {
			log.Warn("instance cpu not sampled: %v", err)
			return 0, false
		}
		return after - before, true
	}
}

// sampleInstanceCPU reads the instance's CPU now and returns what books its use since on p, as the
// instance's CPU over the replay and as apply CPU. The summary leaves it out when the process
// cannot be read or was restarted in between; the port goes on either way.
func (j Job) sampleInstanceCPU(log portLog, port int, replaying bool) func(*portReport) {
	if !replaying {
		return func(*portReport) {}
	}
	since := j.instanceCPUSince(log, port)
	return func(p *portReport) {
		if d, ok := since(); ok {
			p.setInstanceCPU(d)
			p.addCPU(stageApply, d)
		}
	}
}

// timedOnInstance runs fn as stage and books the instance's CPU over it as that stage's: the
// running instance does the work, not a child process.
func (j Job) timedOnInstance(log portLog, p *portReport, port int, stage string, fn func() error) error {
	since := j.instanceCPUSince(log, port)
	err := p.timed(stage, fn)
	if d, ok := since(); ok {
		p.addCPU(stage, d)
	}
	return err
}

// replay runs the kvstores of inst on the host's replay slots, each kvstore on its own connection.
// The first kvstore to fail stops the rest of the port: those still waiting for a slot never take
// one, the running ones stop once the batch they have out is back. Other ports go on.
func (r *plusRestorer) replay(log portLog, p *portReport, inst InstanceRestore, chains map[int][]string,
	recoverAt time.Time, slots chan struct{}) error {
	if len(chains) == 0 {
		return nil
	}
	endMs := replayEndMs(recoverAt)
	kvstores := make([]int, 0, len(chains))
	files := 0
	var bytes int64
	for kvstore, chain := range chains {
		kvstores = append(kvstores, kvstore)
		files += len(chain)
		bytes += totalSize(chain)
	}
	sort.Ints(kvstores)

	var wg sync.WaitGroup
	var errs errCollector
	var mu sync.Mutex
	applied := 0
	redo := false
	stop := make(chan struct{})
	var stopOnce, startOnce sync.Once
	begin := time.Now()
	p.waiting("replay slots")
	for _, kvstore := range kvstores {
		wg.Add(1)
		go func(kvstore int) {
			defer wg.Done()
			select {
			case slots <- struct{}{}:
			case <-stop:
				return
			}
			// Released after a failure has closed stop, so no sibling starts on the freed slot.
			defer func() { <-slots }()
			if stopped(stop) {
				return
			}
			startOnce.Do(func() {
				p.enterReplay(files, bytes, kvProgressOf(chains))
				log.Info("replay %d binlogs (%s), %d kvstores", files, shortBytes(bytes), len(kvstores))
			})
			n, err := r.replayOnConn(log, p, inst.DestPort, kvstore, chains[kvstore], endMs, stop)
			if errors.Is(err, errReplayStopped) {
				err = nil
			}
			mu.Lock()
			applied += n
			redo = redo || failedInFlight(err)
			mu.Unlock()
			if err != nil {
				errs.add(err)
				stopOnce.Do(func() { close(stop) })
			}
		}(kvstore)
	}
	wg.Wait()
	p.replayed(files, replyStats{Lines: applied})
	if slow := p.slowKvstores(); len(slow) > 0 {
		log.Warn("slow kvstores: %s", strings.Join(slow, ", "))
	}
	if redo && !failedInFlight(errs.err) {
		return &inFlightError{errs.err}
	}
	if errs.err == nil {
		log.Info("replayed in %s: %s cmds", shortDuration(time.Since(begin)), shortCount(applied))
	}
	return errs.err
}

// replayOnConn replays one kvstore of port on a connection of its own.
func (r *plusRestorer) replayOnConn(log portLog, p *portReport, port, kvstore int, files []string, endMs int64,
	stop <-chan struct{}) (int, error) {
	cli, closeFn, err := dialPlusFn(r.DestIP, port)
	if err != nil {
		return 0, err
	}
	defer closeFn()
	// Binlogs stream from their downloads; the work dir only keeps binlog_tool's stderr on failure.
	workDir := filepath.Join(r.SaveDir, fmt.Sprintf("binlog_replay_%d_%d", port, kvstore))
	defer os.RemoveAll(workDir)
	return replayKvstore(log, p, cli, kvstore, files, endMs, workDir, stop)
}

// dialPlusFn is replaced in tests, which have no instance to replay into.
var dialPlusFn = dialPlus

func dialPlus(ip string, port int) (plusReplayer, func(), error) {
	password, err := portPassword(port)
	if err != nil {
		return nil, nil, err
	}
	cli, err := myredis.NewRedisClientWithRetry(fmt.Sprintf("%s:%d", ip, port), password, 0,
		consts.TendisTypeTendisplusInsance, plusCommandTimeout)
	if err != nil {
		return nil, nil, err
	}
	return redisReplayer{cli: cli}, cli.Close, nil
}

// restoreEndFn is replaced in tests, which have no instance to connect to.
var restoreEndFn = restoreEnd

// restoreEnd tells every kvstore of a cluster instance that its replay is over. The replay
// brings in whatever the backup held, including chunks of slots this instance does not own;
// restoreend drops those, so it must run after addslots. A non-cluster instance ignores it.
func restoreEnd(log portLog, destIP string, inst InstanceRestore) error {
	password, err := portPassword(inst.DestPort)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", destIP, inst.DestPort)
	cli, err := myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeTendisplusInsance,
		plusCommandTimeout)
	if err != nil {
		return err
	}
	defer cli.Close()
	count, err := cli.GetKvstoreCount()
	if err != nil {
		return err
	}
	kvstores, err := strconv.Atoi(strings.TrimSpace(count))
	if err != nil {
		return fmt.Errorf("invalid kvstorecount %q of %s", count, addr)
	}
	for kvstore := 0; kvstore < kvstores; kvstore++ {
		if err = cli.InstanceClient.Do(context.TODO(), "restoreend", kvstore).Err(); err != nil {
			return fmt.Errorf("restoreend %d on %s failed: %v", kvstore, addr, err)
		}
	}
	log.Info("restoreend done for %d kvstores", kvstores)
	return nil
}

// errReplayStopped ends a kvstore between batches because another kvstore of its port failed.
var errReplayStopped = errors.New("replay stopped: another kvstore of the port failed")

func stopped(stop <-chan struct{}) bool {
	select {
	case <-stop:
		return true
	default:
		return false
	}
}

// plusReplayer is the part of a Tendisplus connection the replay uses.
type plusReplayer interface {
	BinlogPos(kvstore int) (uint64, error)
	// Heartbeat is the time each kvstore holds under the admin key, empty without one.
	Heartbeat(key string) (map[int]time.Time, error)
	pipeExecer
}

type redisReplayer struct {
	cli *myredis.RedisClient
}

// Heartbeat reads key with adminget, which answers one (kvstore, unix seconds) pair per kvstore.
func (c redisReplayer) Heartbeat(key string) (map[int]time.Time, error) {
	ret, err := c.cli.InstanceClient.Do(context.TODO(), "adminget", key).Result()
	if errors.Is(err, redis.Nil) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("adminget %s on %s failed: %v", key, c.cli.Addr, err)
	}
	return parseHeartbeat(key, ret)
}

// parseHeartbeat reads an adminget reply; a kvstore whose value is missing or not a number has none.
func parseHeartbeat(key string, ret interface{}) (map[int]time.Time, error) {
	if ret == nil {
		return nil, nil
	}
	pairs, ok := ret.([]interface{})
	if !ok {
		return nil, fmt.Errorf("adminget %s returned %v, want (kvstore, timestamp) pairs", key, ret)
	}
	beats := map[int]time.Time{}
	for _, item := range pairs {
		pair, ok := item.([]interface{})
		if !ok || len(pair) != 2 {
			return nil, fmt.Errorf("adminget %s returned %v, want (kvstore, timestamp) pairs", key, ret)
		}
		kvstore, err := strconv.Atoi(fmt.Sprint(pair[0]))
		if err != nil {
			return nil, fmt.Errorf("adminget %s returned kvstore %v", key, pair[0])
		}
		if pair[1] == nil {
			continue
		}
		if sec, err := strconv.ParseInt(strings.TrimSpace(fmt.Sprint(pair[1])), 10, 64); err == nil {
			beats[kvstore] = time.Unix(sec, 0)
		}
	}
	return beats, nil
}

// BinlogPos is the highest binlog id kvstore holds.
func (c redisReplayer) BinlogPos(kvstore int) (uint64, error) {
	ret, err := c.cli.InstanceClient.Do(context.TODO(), "binlogpos", kvstore).Result()
	if err != nil {
		return 0, fmt.Errorf("binlogpos %d on %s failed: %v", kvstore, c.cli.Addr, err)
	}
	switch v := ret.(type) {
	case int64:
		if v >= 0 {
			return uint64(v), nil
		}
	case string:
		if pos, err := strconv.ParseUint(strings.TrimSpace(v), 10, 64); err == nil {
			return pos, nil
		}
	}
	return 0, fmt.Errorf("binlogpos %d on %s returned %v", kvstore, c.cli.Addr, ret)
}

// execBatch pipelines restorebinlogv2 commands on one connection, which keeps their order.
func (c redisReplayer) execBatch(cmds [][]string) ([]error, error) {
	return redisPipe{cli: c.cli.InstanceClient}.execBatch(cmds)
}

// binlogToolFn is replaced in tests, which have no binlog_tool.
var binlogToolFn = runBinlogToolStream

// replayKvstore replays a kvstore's binlogs in index order, each starting right after the highest
// binlog id already in the kvstore, so a retry carries on without replaying anything twice and
// every error reply is a real one. Ending binlogpos must be the last id sent: binlog_tool exits 0
// on a binlog it cannot decode, and this also catches anything else that skipped writes.
// Commands go in batches flushed at the end of each file. The server does not refuse a gap in
// ids, so once a batch fails while out, or binlog ids and binlogpos disagree, the error is an
// inFlightError and binlogpos cannot be resumed from; failing between batches drops the unsent
// part and leaves binlogpos exact. A closed stop ends it that way with errReplayStopped. Its
// errors go to the detail file too, all but errReplayStopped.
func replayKvstore(log portLog, p *portReport, cli plusReplayer, kvstore int, files []string, endMs int64,
	workDir string, stop <-chan struct{}) (applied int, err error) {
	defer func() {
		if err != nil && !errors.Is(err, errReplayStopped) {
			p.detail("ERROR kv=%d: %v", kvstore, err)
		}
	}()
	// Sending batches runs on this goroutine alone; locked to its thread, the thread's CPU is this
	// kvstore's.
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	if err = os.MkdirAll(workDir, 0755); err != nil {
		return 0, err
	}
	p.kvstoreStarted(kvstore)
	start, err := cli.BinlogPos(kvstore)
	if err != nil {
		return 0, err
	}
	last, first, replayed := start, true, 0
	defer func() { p.kvstoreReplayed(kvstore, replayed, applied, start, last) }()
	var batches, batchCPU time.Duration
	exec := timedExec{exec: cli, onBatch: func(wall, cpu time.Duration) {
		batches += wall
		batchCPU += cpu
	}}
	pipe := &commandPipe{exec: exec, onReply: func(args []string, _ cmdOrigin, reply error) error {
		if reply != nil {
			id, _ := binlogIDFromKey(args[2])
			return fmt.Errorf("%s of binlog id %d failed: %v", restoreBinlogCmd, id, reply)
		}
		applied++
		return nil
	}}
	for _, file := range files {
		if stopped(stop) {
			return applied, errReplayStopped
		}
		base := filepath.Base(file)
		begin, batchesBefore, batchCPUBefore, appliedBefore := time.Now(), batches, batchCPU, applied
		cpu, err := binlogToolFn(file, workDir, last+1, endMs, func(line string) error {
			args, id, err := parseRestoreLine(line, kvstore)
			if err != nil || args == nil {
				return err
			}
			if id <= last {
				return &inFlightError{fmt.Errorf("binlog id %d is not after %d though binlog_tool started "+
					"after it; binlog ids may not be read right from %s keys", id, last, restoreBinlogCmd)}
			}
			if stopped(stop) {
				return errReplayStopped
			}
			if first && id != start+1 {
				log.Warn("kv%d resumes at binlog id %d, binlogpos was %d", kvstore, id, start)
			}
			first = false
			last = id
			return pipe.add(args)
		})
		if err == nil && stopped(stop) {
			err = errReplayStopped
		}
		if err == nil {
			err = pipe.flush()
		}
		apply := batches - batchesBefore
		p.addKvstore(kvstore, stageParse, 0, cpu.parse)
		p.addKvstore(kvstore, stageDecode, time.Since(begin)-apply, cpu.decode)
		p.addKvstore(kvstore, stageApply, apply, batchCPU-batchCPUBefore)
		failed := 0
		if err != nil {
			failed = 1
		}
		p.detail("kv=%d %s cmds=%d errors=%d wall=%s", kvstore, base, applied-appliedBefore, failed,
			time.Since(begin).Round(time.Millisecond))
		if err != nil {
			return applied, fmt.Errorf("kvstore %d binlog %s: %w", kvstore, base, err)
		}
		p.kvstoreBinlogReplayed(kvstore, totalSize([]string{file}))
		replayed++
	}
	pos, err := cli.BinlogPos(kvstore)
	if err != nil {
		return applied, err
	}
	p.kvstoreAfter(kvstore, pos)
	if pos != last {
		return applied, &inFlightError{fmt.Errorf("kvstore %d binlogpos is %d after replay, want %d, the last "+
			"binlog id replayed", kvstore, pos, last)}
	}
	p.kvstoreFinished(kvstore)
	return applied, nil
}

// parseRestoreLine reads one line of binlog_tool --mode=base64 output:
// "restorebinlogv2 <kvstore> <base64 key> <base64 value>". A blank line gives no args.
func parseRestoreLine(line string, kvstore int) ([]string, uint64, error) {
	fields := strings.Fields(line)
	if len(fields) == 0 {
		return nil, 0, nil
	}
	if len(fields) < 4 || !strings.EqualFold(fields[0], restoreBinlogCmd) {
		const shown = 200
		if len(line) > shown {
			line = line[:shown] + "..."
		}
		return nil, 0, fmt.Errorf("binlog_tool printed %q instead of a %s command, as it does when it "+
			"cannot decode a binlog", line, restoreBinlogCmd)
	}
	if fields[1] != strconv.Itoa(kvstore) {
		return nil, 0, fmt.Errorf("binlog_tool printed a command for kvstore %s, want %d", fields[1], kvstore)
	}
	id, err := binlogIDFromKey(fields[2])
	if err != nil {
		return nil, 0, err
	}
	return fields, id, nil
}

// binlogIDFromKey reads the binlog id out of a base64 ReplLogKeyV2.
func binlogIDFromKey(key string) (uint64, error) {
	raw, err := base64.StdEncoding.DecodeString(key)
	if err != nil {
		return 0, fmt.Errorf("binlog key %.40q is not base64: %v", key, err)
	}
	if len(raw) < binlogIDOffset+8 {
		return 0, fmt.Errorf("binlog key %.40q is %d bytes, too short to hold a binlog id", key, len(raw))
	}
	id := binary.BigEndian.Uint64(raw[binlogIDOffset : binlogIDOffset+8])
	if id == 0 {
		return 0, fmt.Errorf("binlog key %.40q holds binlog id 0", key)
	}
	return id, nil
}

// plusBinlogToolFn is replaced in tests, which run a script in its place.
var plusBinlogToolFn = plusBinlogTool

// plusBinlogTool prefers the binlog_tool of the instance's own media, then the dbtools copy.
func plusBinlogTool() (string, error) {
	media := filepath.Join(consts.UsrLocal, "redis", "bin", "binlog_tool")
	for _, bin := range []string{media, consts.BinlogToolTendisplusBin} {
		if util.FileExists(bin) {
			return bin, nil
		}
	}
	return "", fmt.Errorf("binlog_tool not found: %s or %s", media, consts.BinlogToolTendisplusBin)
}

// streamCPU is the CPU a binlog's replay took outside the instance: the decompressor's (parse)
// and binlog_tool's (decode).
type streamCPU struct {
	parse  time.Duration
	decode time.Duration
}

// binlogDecompressor is the command writing file decompressed to its stdout, nil for a binlog
// stored as is, which binlog_tool reads itself.
func binlogDecompressor(ctx context.Context, file string) (*exec.Cmd, error) {
	var bin string
	switch {
	case strings.HasSuffix(file, ".zst"):
		bin = consts.ZstdBin
	case strings.HasSuffix(file, ".lzo"):
		bin = consts.LzopBin
	case strings.HasSuffix(file, ".gz"):
		return exec.CommandContext(ctx, "gzip", "-dc", file), nil
	default:
		return nil, nil
	}
	if _, err := os.Stat(bin); err != nil {
		return nil, fmt.Errorf("%s not found: %s", strings.TrimPrefix(filepath.Ext(file), "."), bin)
	}
	return exec.CommandContext(ctx, bin, "-dc", file), nil
}

// streamWaitDelay bounds how long a killed decompressor or binlog_tool may keep its pipes open.
const streamWaitDelay = 5 * time.Second

// runBinlogToolStream streams the restorebinlogv2 commands of a downloaded binlog from startPos
// on, up to endMs exclusive, into onLine. The binlog is decompressed into binlog_tool's stdin, so
// nothing decompressed lands on disk. The first onLine error stops both and is returned. A
// decompressor failing, as on a truncated file, fails the binlog as corrupted even when
// binlog_tool took the short input and exited 0; workDir keeps binlog_tool's stderr on failure.
func runBinlogToolStream(file, workDir string, startPos uint64, endMs int64,
	onLine func(string) error) (streamCPU, error) {
	var cpu streamCPU
	bin, err := plusBinlogToolFn()
	if err != nil {
		return cpu, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), plusToolTimeout)
	defer cancel()
	unpack, err := binlogDecompressor(ctx, file)
	if err != nil {
		return cpu, err
	}
	logFile := file
	if unpack != nil {
		logFile = "/dev/stdin"
	}
	tool := exec.CommandContext(ctx, bin, "--logfile="+logFile, "--mode=base64",
		fmt.Sprintf("--start-position=%d", startPos), fmt.Sprintf("--end-datetime=%d", endMs))
	stdout, err := tool.StdoutPipe()
	if err != nil {
		return cpu, err
	}
	// Cancelling kills the tool but not what it started: without WaitDelay, a child still holding
	// its stderr would keep Wait from returning.
	tool.WaitDelay = streamWaitDelay
	var toolErr, unpackErr bytes.Buffer
	tool.Stderr = &toolErr
	var src io.ReadCloser
	var dst io.WriteCloser
	if unpack != nil {
		unpack.WaitDelay = streamWaitDelay
		unpack.Stderr = &unpackErr
		if src, err = unpack.StdoutPipe(); err != nil {
			return cpu, err
		}
		if dst, err = tool.StdinPipe(); err != nil {
			return cpu, err
		}
	}
	if err = tool.Start(); err != nil {
		return cpu, err
	}
	copied := make(chan struct{})
	if unpack == nil {
		close(copied)
	} else if err = unpack.Start(); err != nil {
		_ = dst.Close()
		cancel()
		_ = tool.Wait()
		return cpu, err
	} else {
		go func() {
			defer close(copied)
			_, err := io.Copy(dst, src)
			_ = dst.Close()
			if err != nil {
				// binlog_tool stopped reading, at end-datetime or on failure: drain the rest so
				// the decompressor's exit status still covers the whole file.
				_, _ = io.Copy(io.Discard, src)
			}
		}()
	}

	reader := bufio.NewReaderSize(stdout, 1<<20)
	var lineErr error
	for {
		line, readErr := reader.ReadString('\n')
		if line != "" {
			if lineErr = onLine(strings.TrimRight(line, "\r\n")); lineErr != nil {
				cancel()
				break
			}
		}
		if readErr == io.EOF {
			break
		}
		if readErr != nil {
			lineErr = readErr
			cancel()
			break
		}
	}
	waitErr := tool.Wait()
	cpu.decode = cpuTime(tool)
	<-copied
	var unpackWait error
	if unpack != nil {
		unpackWait = unpack.Wait()
		cpu.parse = cpuTime(unpack)
	}
	base := filepath.Base(file)
	switch {
	case lineErr != nil:
		return cpu, lineErr
	case unpackWait != nil:
		return cpu, corrupted(base, fmt.Errorf("%v %s", unpackWait, strings.TrimSpace(unpackErr.String())))
	case waitErr != nil || strings.Contains(toolErr.String(), "ERR"):
		return cpu, fmt.Errorf("%s failed: %v %s", filepath.Base(bin), waitErr,
			keepOutput(workDir, base+".tool.err", toolErr.Bytes()))
	}
	return cpu, nil
}

// LocalKvstoreBinlogs returns every kvstore's downloaded binlogs in replay order, each chain checked
// against its planned digest on its own, and the indexes the chains allowGaps lets through skip,
// by kvstore (see checkChain).
func LocalKvstoreBinlogs(saveDir string, inst InstanceRestore, allowGaps *bool) (chains map[int][]string,
	gaps map[int][]int64, err error) {
	if len(inst.KvstoreBinlogs) == 0 {
		return nil, nil, nil
	}
	paths, err := filepath.Glob(filepath.Join(saveDir, "binlog-*"))
	if err != nil {
		return nil, nil, err
	}
	found := map[int][]localBinlog{}
	for _, p := range paths {
		m := plusBinlogReg.FindStringSubmatch(filepath.Base(p))
		if m == nil || (m[1] != "" && m[1] != inst.SourceIP) || m[2] != strconv.Itoa(inst.SourcePort) {
			continue
		}
		kvstore, _ := strconv.Atoi(m[3])
		idx, _ := strconv.ParseInt(m[4], 10, 64)
		found[kvstore] = append(found[kvstore], localBinlog{p, idx})
	}
	chains = make(map[int][]string, len(inst.KvstoreBinlogs))
	for _, d := range inst.KvstoreBinlogs {
		files, missing, err := checkChain(saveDir, found[d.Kvstore], chainDigest{
			label:       fmt.Sprintf("%s:%d kvstore %d", inst.SourceIP, inst.SourcePort, d.Kvstore),
			rng:         d.BinlogRange,
			count:       d.BinlogCount,
			fingerprint: d.BinlogFingerprint,
			segments:    d.BinlogSegments,
			allowGaps:   allowGaps,
		})
		if err != nil {
			return nil, nil, err
		}
		chains[d.Kvstore] = files
		if len(missing) > 0 {
			if gaps == nil {
				gaps = map[int][]int64{}
			}
			gaps[d.Kvstore] = missing
		}
	}
	return chains, gaps, nil
}
