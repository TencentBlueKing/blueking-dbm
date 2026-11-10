// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
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
	report := r.newReport(engineSSD)
	defer report.logResult()

	redo, err := r.resolvePending(report)
	if err != nil {
		return err
	}
	if len(redo) == 0 {
		logInfo("RedisRollback: all ports already rolled back")
		return nil
	}

	binlogs := make(map[int][]string, len(redo))
	plans := make(map[int]portPlan, len(redo))
	for _, inst := range redo {
		var gaps []int64
		if binlogs[inst.DestPort], gaps, err = LocalBinlogs(r.SaveDir, inst, r.AllowBinlogNonconsecutive); err != nil {
			report.port(inst.DestPort).finish(err)
			return err
		}
		if len(gaps) > 0 {
			report.port(inst.DestPort).allowedGaps("", gaps)
			newPortLog(inst.DestPort).Warn("binlogs skip %s, as the plan allows: the temp instance misses "+
				"their writes", indexRanges(gaps))
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
	if err = r.applyTuning(portsOf(redo)); err != nil {
		return err
	}
	for _, inst := range redo {
		plan := plans[inst.DestPort]
		plan.memory = SSDMemory(confFile(r.Host.InstanceDir(inst.DestPort)))
		plans[inst.DestPort] = plan
	}
	replaying := limits.Replay(len(redo))
	report.tuning = r.tuningSummary()
	report.logPlan(limits, plans, r.UnpackDir, fmt.Sprintf("%d ports at once, most binlog bytes first", replaying))
	defer report.trackProgress()()

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
			p.waiting("replay slots")
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
				newPortLog(inst.DestPort).Info("skip: already rolled back to this point")
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
	log := newPortLog(inst.DestPort)
	instDir := r.Host.InstanceDir(inst.DestPort)
	workDir := r.portWorkDir(inst.DestPort)
	if len(inst.FullFiles) > 0 {
		var root string
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
			root, err = ssdBackupRoot(workDir)
			return err
		})
		if err != nil {
			log.Error("unpack failed: %v", err)
			return err
		}
		log.Info("unpacked %s in %s", shortBytes(size), shortDuration(p.duration(stageUnpack)))
		p.enter(phaseRestore, 0, "")
		err = p.timed(stageRestore, func() error {
			cpu, err := restoreRocksdb(r.Host.MediaName(), root, ssdDataDir(instDir), workDir)
			p.addCPU(stageRestore, cpu)
			return err
		})
		if err != nil {
			log.Error("restore failed: %v", err)
			p.detail("ERROR restore: %v", err)
			return err
		}
		log.Info("restored rocksdb in %s", shortDuration(p.duration(stageRestore)))
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
	p.enter(phaseStart, 0, "")
	if err := p.timed(stageStart, func() error { return r.Host.Start(inst.DestPort) }); err != nil {
		window.unreserve(need)
		log.Error("start failed: %v", err)
		return err
	}
	log.Info("started, memory~%s", shortBytes(need))
	return nil
}

// ssdReplayFn is replaced in tests, which have no instance to replay into.
var ssdReplayFn = (*ssdRestorer).replay

// replayAndMark replays inst's binlogs, then marks it done and frees its downloads. The
// instance's CPU over the replay is booked on p when its process can be read.
func (r *ssdRestorer) replayAndMark(inst InstanceRestore, p *portReport, binlogs []string,
	recoverAt time.Time) error {
	log := newPortLog(inst.DestPort)
	// Earlier attempts on older media kept the decompressed binlog and its commands here.
	_ = os.RemoveAll(filepath.Join(r.SaveDir, fmt.Sprintf("binlog_replay_%d", inst.DestPort)))
	if len(binlogs) > 0 {
		sample := r.sampleInstanceCPU(log, inst.DestPort, true)
		err := ssdReplayFn(r, log, p, inst, recoverAt, binlogs)
		sample(p)
		if err != nil {
			log.Error("failed: %v", err)
			return err
		}
	}
	if len(inst.FullFiles) > 0 || len(binlogs) > 0 {
		r.checkHeartbeat(log, p, inst, recoverAt)
	}
	instDir := r.Host.InstanceDir(inst.DestPort)
	if err := MarkDone(instDir, r.fingerprint(inst)); err != nil {
		log.Error("failed: %v", err)
		return err
	}
	if err := CleanupStaged(r.SaveDir, r.portWorkDir(inst.DestPort), inst); err != nil {
		log.Warn("cleanup staged files failed: %v", err)
	}
	for _, f := range binlogs {
		_ = os.Remove(f)
	}
	log.Info("done")
	return nil
}

// checkHeartbeat compares the source heartbeat the restored instance holds with recoverAt, as v1
// does: dbmon writes <ip>:<port>:time and <ip>:<port>:0:dbsize on the source, in db 0 where
// TendisSSD keeps every key. Like Tendisplus, a heartbeat out of the tolerance, or one that
// cannot be read, is a warning on the port and never fails it; a source that wrote none is
// logged and not checked.
func (r *ssdRestorer) checkHeartbeat(log portLog, p *portReport, inst InstanceRestore, recoverAt time.Time) {
	src := fmt.Sprintf("%s:%d", inst.SourceIP, inst.SourcePort)
	timeKey, dbsizeKey := src+":time", src+":0:dbsize"
	beat, dbsize, err := ssdHeartbeatFn(r.DestIP, inst.DestPort, timeKey, dbsizeKey)
	if err != nil {
		p.heartbeatOff(log, "heartbeat %s not read: %v", timeKey, err)
		return
	}
	if beat.IsZero() {
		log.Info("no heartbeat under %s, heartbeat check skipped", timeKey)
		return
	}
	p.setHeartbeat(beat, dbsize)
	tolerance := r.heartbeatTolerance()
	if beatOff(beat, recoverAt, tolerance) {
		p.heartbeatOff(log, "heartbeat %s at %s is more than %s from recover_at %s", timeKey,
			beat.Local().Format(time.RFC3339), tolerance, recoverAt.Local().Format(time.RFC3339))
		return
	}
	log.Info("heartbeat %s within %s of recover_at (dbsize %d)", timeKey, tolerance, dbsize)
}

// ssdHeartbeatFn is replaced in tests, which have no instance to read from.
var ssdHeartbeatFn = readSSDHeartbeat

// readSSDHeartbeat reads the source heartbeat and dbsize keys from the instance's db 0. A port
// with no binlogs is read right after its start, while rocksdb may still be loading.
func readSSDHeartbeat(ip string, port int, timeKey, dbsizeKey string) (time.Time, int64, error) {
	addr := fmt.Sprintf("%s:%d", ip, port)
	password, err := portPassword(port)
	if err != nil {
		return time.Time{}, -1, err
	}
	end := time.Now().Add(minLoadDeadline)
	cli, err := connectWithin(addr, password, consts.TendisTypeTendisSSDInsance, minLoadDeadline)
	if err != nil {
		return time.Time{}, -1, err
	}
	defer cli.Close()
	vals, err := retryWhileLoading(func() ([]interface{}, error) {
		return cli.InstanceClient.MGet(context.TODO(), timeKey, dbsizeKey).Result()
	}, end, loadPollInterval)
	if err != nil {
		return time.Time{}, -1, fmt.Errorf("mget %s %s on %s failed: %v", timeKey, dbsizeKey, addr, err)
	}
	return parseSSDHeartbeat(timeKey, vals)
}

// retryWhileLoading calls mget until it stops failing with LOADING or end passes. Redis accepts
// connections while loading but rejects data commands.
func retryWhileLoading(mget func() ([]interface{}, error), end time.Time,
	interval time.Duration) ([]interface{}, error) {
	for {
		vals, err := mget()
		if err == nil || !strings.Contains(err.Error(), "LOADING") || !time.Now().Add(interval).Before(end) {
			return vals, err
		}
		time.Sleep(interval)
	}
}

// parseSSDHeartbeat reads an MGET of the time and dbsize keys. The time is unix seconds, or
// milliseconds when it is that large; a missing time is zero and a missing dbsize -1.
func parseSSDHeartbeat(timeKey string, vals []interface{}) (time.Time, int64, error) {
	if len(vals) != 2 {
		return time.Time{}, -1, fmt.Errorf("mget %s returned %v, want time and dbsize", timeKey, vals)
	}
	var beat time.Time
	if vals[0] != nil {
		n, err := strconv.ParseInt(strings.TrimSpace(fmt.Sprint(vals[0])), 10, 64)
		if err != nil {
			return time.Time{}, -1, fmt.Errorf("%s holds %q, not a unix time", timeKey, fmt.Sprint(vals[0]))
		}
		if n > 1e12 {
			beat = time.UnixMilli(n)
		} else {
			beat = time.Unix(n, 0)
		}
	}
	dbsize := int64(-1)
	if vals[1] != nil {
		if n, err := strconv.ParseInt(strings.TrimSpace(fmt.Sprint(vals[1])), 10, 64); err == nil {
			dbsize = n
		}
	}
	return beat, dbsize, nil
}

// replay finds where the restored instance's binlog ends and replays binlogs from there over
// one connection (see replayFiles).
func (r *ssdRestorer) replay(log portLog, p *portReport, inst InstanceRestore, recoverAt time.Time,
	binlogs []string) error {
	port := inst.DestPort
	addr := fmt.Sprintf("%s:%d", r.DestIP, port)
	password, err := portPassword(port)
	if err != nil {
		return err
	}
	cli, err := connectWithin(addr, password, consts.TendisTypeTendisSSDInsance, minLoadDeadline)
	if err != nil {
		return err
	}
	start, err := replayStart(log, func() (uint64, error) {
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
	start.endMs = replayEndMs(recoverAt)
	return replayFiles(log, p, redisPipe{cli: applyCli.InstanceClient}, binlogs, start)
}

// replayFiles decodes binlogs in index order and sends their commands through exec, from
// start.startSeq up to start.endMs. Like v1, error replies are counted rather than failing the
// port, unless every reply of a file is an error; the node log shows the first reply of each kind
// and the summary counts them, while each binlog gets a line in the detail file, as do the error
// replies (up to detailMaxReplies) and a failing binlog's error. Each file is streamed straight
// into the connection, so nothing is written to disk between decoding and sending. The Go
// decoder's CPU is booked as decode and the client side of the batches as apply.
func replayFiles(log portLog, p *portReport, exec pipeExecer, binlogs []string, start ssdReplayReport) error {
	// Decoding and sending run on this goroutine alone; locked to its thread, the thread's CPU is
	// this port's.
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	bytes := totalSize(binlogs)
	p.enterReplay(len(binlogs), bytes, nil)
	log.Info("replay %d binlogs (%s) after seq %d", len(binlogs), shortBytes(bytes), start.startSeq-1)
	began := time.Now()
	var total replyStats
	var seen bool
	defer func() {
		p.replayed(len(binlogs), total)
		p.setSSD(start)
		p.noteOmittedReplies()
	}()
	for _, file := range binlogs {
		base := filepath.Base(file)
		begin := time.Now()
		var applyWall, applyCPU time.Duration
		var fileStats replyStats
		pipe := &commandPipe{
			exec: timedExec{exec: exec, onBatch: func(wall, cpu time.Duration) {
				applyWall += wall
				applyCPU += cpu
				p.add(stageApply, wall)
				p.addCPU(stageApply, cpu)
			}},
			onReply: func(args []string, from cmdOrigin, reply error) error {
				fileStats.Lines++
				if reply != nil {
					preview := commandPreview(args)
					fileStats.record(reply.Error(), preview)
					p.detailReply("  error [%s] seq=%d ts=%s (error) %s <- %s", base, from.seq,
						recordTime(from.ts), reply.Error(), preview)
					if kind := errorKind(reply.Error()); p.firstReply(kind) {
						line := fmt.Sprintf("first %q reply in %s: (error) %s <- %s", kind, base,
							previewLine(reply.Error()), preview)
						if kind == expectedReplyError {
							log.Info("%s", line)
						} else {
							log.Warn("%s", line)
						}
					}
				}
				return nil
			},
		}
		decodeCPU := threadCPU()
		stats, cpu, err := decodeSSDFile(file, start.startSeq, start.endMs, func(rec *ssdBinlogRecord) error {
			args, skip, err := rec.command(time.Now().UnixMilli())
			if err != nil {
				return fmt.Errorf("seq %d: %v", rec.seq, err)
			}
			if skip {
				return nil
			}
			return pipe.addFrom(args, cmdOrigin{seq: rec.seq, ts: rec.ts})
		})
		if err == nil {
			err = pipe.flush()
		}
		p.addCPU(stageDecode, threadCPU()-decodeCPU-applyCPU)
		p.addCPU(stageParse, cpu)
		p.add(stageParse, stats.readTime)
		p.add(stageDecode, time.Since(begin)-stats.readTime-applyWall)
		p.detail("%s records=%d cmds=%d errors=%d wall=%s", base, stats.records, fileStats.Lines,
			fileStats.Errors, time.Since(begin).Round(time.Millisecond))
		total.add(fileStats)
		if stats.records > 0 {
			if !seen {
				start.firstSeq, seen = stats.firstSeq, true
			}
			start.lastSeq, start.lastFile = stats.lastSeq, base
		}
		if err == nil && fileStats.Lines > 0 && fileStats.Errors == fileStats.Lines {
			err = fmt.Errorf("all %d replies are errors, samples %q", fileStats.Lines, fileStats.samples())
		}
		if err != nil {
			p.detail("ERROR %s: %v", base, err)
			return fmt.Errorf("binlog %s: %w", base, err)
		}
		p.binlogReplayed(totalSize([]string{file}))
	}
	if n := total.Errors - total.Expected; n > 0 {
		log.Warn("replayed in %s: seq %d -> %d, %d error replies, writes may be missing",
			shortDuration(time.Since(began)), start.firstSeq, start.lastSeq, n)
	} else {
		log.Info("replayed in %s: seq %d -> %d, %s cmds", shortDuration(time.Since(began)), start.firstSeq,
			start.lastSeq, shortCount(total.Lines))
	}
	return nil
}

// replayStartPos is the first binlog seq not yet in the restored snapshot (see replayStart).
func replayStartPos(log portLog, endSeq func() (uint64, error), fullFiles []string) (uint64, error) {
	start, err := replayStart(log, endSeq, fullFiles)
	return start.startSeq, err
}

// replayStart is where the replay starts: after the last seq already in the restored snapshot.
// The seq in the full backup name is the last one already written when the backup began, so
// replay starts after it. The restored instance's own end seq is preferred; a reason is logged
// when it is not used or the two differ.
func replayStart(log portLog, endSeq func() (uint64, error), fullFiles []string) (ssdReplayReport, error) {
	nameSeq, nameErr := fullStartPos(fullFiles)
	seq, err := endSeq()
	if err == nil && seq == 0 {
		err = fmt.Errorf("binlogsize returned end seq 0")
	}
	start := ssdReplayReport{nameSeq: nameSeq}
	if err == nil {
		start.restoredSeq = seq
	}
	switch {
	case err != nil && nameErr != nil:
		return start, fmt.Errorf("no replay start position, binlogsize: %v; %v", err, nameErr)
	case err != nil:
		log.Warn("start after backup name seq %d: binlogsize unavailable: %v", nameSeq, err)
		start.startSeq, start.from = nameSeq+1, "backup name"
	case nameErr != nil:
		log.Warn("start after restored end seq %d: %v", seq, nameErr)
		start.startSeq, start.from = seq+1, "restored"
	case seq < nameSeq:
		// Everything up to nameSeq is in the snapshot; starting earlier would replay it again.
		log.Warn("start after backup name seq %d: restored end seq %d is behind it", nameSeq, seq)
		start.startSeq, start.from = nameSeq+1, "backup name"
	case seq > nameSeq:
		log.Warn("start after restored end seq %d: ahead of backup name seq %d", seq, nameSeq)
		start.startSeq, start.from = seq+1, "restored"
	default:
		start.startSeq, start.from = seq+1, "restored"
	}
	return start, nil
}

// replayEndMs is the exclusive end of the replay window: one second after recoverAt keeps the
// writes made within the recoverAt second, as v1 does.
func replayEndMs(recoverAt time.Time) int64 {
	return recoverAt.Add(time.Second).UnixMilli()
}

// recordTime is a binlog record's write time in ms, in local time; "-" when unknown.
func recordTime(ms int64) string {
	if ms <= 0 {
		return "-"
	}
	return time.UnixMilli(ms).Format("2006-01-02 15:04:05.000")
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
// exactly the chain the plan was built on: same count and same fingerprint. allowGaps is the
// plan's allow_binlog_nonconsecutive (see checkChain); the indexes a chain it allows skips come
// back as gaps.
func LocalBinlogs(saveDir string, inst InstanceRestore, allowGaps *bool) (files []string, gaps []int64,
	err error) {
	if inst.BinlogCount == 0 {
		return nil, nil, nil
	}
	paths, err := filepath.Glob(filepath.Join(saveDir, "binlog-*"))
	if err != nil {
		return nil, nil, err
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
		allowGaps:   allowGaps,
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
	// allowGaps is the plan's allow_binlog_nonconsecutive, nil when the payload predates it.
	allowGaps *bool
}

// checkChain keeps the binlogs of found within the planned range, in index order, and requires
// them to be the planned chain. Unless allowGaps is nil, the chain must also run index by index
// from the planned first to the planned last, before anything is written: a skipped index fails
// it unless allowGaps is true, which returns the skipped indexes instead; a repeated one always
// fails it.
func checkChain(saveDir string, found []localBinlog, d chainDigest) ([]string, []int64, error) {
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
	var missing, duplicate []int64
	for idx := d.rng.FirstIndex; idx <= d.rng.LastIndex; idx++ {
		switch n := seen[idx]; {
		case n == 0:
			missing = append(missing, idx)
		case n > 1:
			duplicate = append(duplicate, idx)
		}
	}
	if len(chain) != d.count || BinlogFingerprint(names) != d.fingerprint {
		return nil, nil, fmt.Errorf("binlogs of %s in %s differ from the plan: want %d as %s, got %d, "+
			"missing %v (planned gaps included), duplicate %v",
			d.label, saveDir, d.count, d.segments, len(chain), missing, duplicate)
	}
	switch {
	case d.allowGaps == nil || len(missing) == 0 && len(duplicate) == 0:
		return files, nil, nil
	case len(duplicate) > 0:
		return nil, nil, fmt.Errorf("binlogs of %s repeat index %s", d.label, indexRanges(duplicate))
	case !*d.allowGaps:
		return nil, nil, fmt.Errorf("binlogs of %s skip %s, not allowed by the plan: %s", d.label,
			indexRanges(missing), strings.Join(chainHoles(chain, d.rng), ", "))
	}
	return files, missing, nil
}

// chainHolesShown caps the holes named in an error; the indexes themselves are all listed.
const chainHolesShown = 3

// chainHoles names each run of skipped indexes by the file right after it.
func chainHoles(chain []localBinlog, rng BinlogRange) []string {
	var holes []string
	next := rng.FirstIndex
	for _, b := range chain {
		if b.index > next {
			holes = append(holes, fmt.Sprintf("%s before %s", indexRun(next, b.index-1), filepath.Base(b.path)))
		}
		if b.index >= next {
			next = b.index + 1
		}
	}
	if next <= rng.LastIndex {
		holes = append(holes, fmt.Sprintf("%s after the last file", indexRun(next, rng.LastIndex)))
	}
	if len(holes) > chainHolesShown {
		holes = append(holes[:chainHolesShown], fmt.Sprintf("...(+%d)", len(holes)-chainHolesShown))
	}
	return holes
}

// indexRunsShown caps the runs indexRanges writes out.
const indexRunsShown = 5

// indexRanges writes ascending indexes as runs, e.g. #31-33,#40, the ones past indexRunsShown
// runs as a count.
func indexRanges(indexes []int64) string {
	var runs []string
	for i := 0; i < len(indexes); {
		j := i
		for j+1 < len(indexes) && indexes[j+1] == indexes[j]+1 {
			j++
		}
		if len(runs) == indexRunsShown {
			runs = append(runs, fmt.Sprintf("...(+%d)", len(indexes)-i))
			break
		}
		runs = append(runs, indexRun(indexes[i], indexes[j]))
		i = j + 1
	}
	return strings.Join(runs, ",")
}

func indexRun(first, last int64) string {
	if first == last {
		return fmt.Sprintf("#%d", first)
	}
	return fmt.Sprintf("#%d-%d", first, last)
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

// ssdBinDir holds the media's tools; tests point it at scripts.
var ssdBinDir = filepath.Join(consts.UsrLocal, "redis", "bin")

// ssdRestoreTool picks the rocksdb restore command for the media: v1.2 and v1.3 ship different tools.
func ssdRestoreTool(media string) (string, error) {
	bin := ssdBinDir
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

// restoreRocksdb replaces dataDir/rocksdb with the one rebuilt from backupRoot and returns the
// CPU the restore tool used, on failure too. The tool's output is kept in workDir, and its command
// line is in the error when it fails.
func restoreRocksdb(media, backupRoot, dataDir, workDir string) (time.Duration, error) {
	tool, err := ssdRestoreTool(media)
	if err != nil {
		return 0, err
	}
	rocksdbDir := filepath.Join(dataDir, "rocksdb")
	if err = os.RemoveAll(rocksdbDir); err != nil {
		return 0, err
	}
	cmd := strings.Join(ssdToolEnv(), " ") + " " + fmt.Sprintf(tool, backupRoot, rocksdbDir)
	out, cpu, err := runStageOutput(cmd, nil, ssdCmdTimeout)
	if err != nil || strings.Contains(out, "ERR:") {
		return cpu, fmt.Errorf("restore rocksdb from %s failed: %v %s; command: %s", backupRoot, err,
			keepOutput(workDir, "restore.out", []byte(out)), cmd)
	}
	if !util.FileExists(rocksdbDir) {
		return cpu, fmt.Errorf("restore rocksdb from %s produced no %s", backupRoot, rocksdbDir)
	}
	return cpu, util.LocalDirChownMysql(dataDir)
}

const replyErrorSamples = 2

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
