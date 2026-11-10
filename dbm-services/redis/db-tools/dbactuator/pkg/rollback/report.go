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
	"sort"
	"strings"
	"sync"
	"syscall"
	"time"
)

// Stages timed per port in the end-of-node summary. Download time is the download node's: the
// backup system lands a host's files together, not port by port. A Tendisplus binlog streams
// through all three replay stages at once: parse is the decompressor and has CPU only, decode is
// binlog_tool and the time not spent waiting on the instance, apply is the time batches are out.
const (
	stageUnpack  = "unpack"
	stageRestore = "restore"
	stageStart   = "start"
	stageParse   = "parse"
	stageDecode  = "decode"
	stageApply   = "apply"
)

var stageOrder = []string{stageUnpack, stageRestore, stageStart, stageParse, stageDecode, stageApply}

// resultStages are the stage columns of an engine's result table. A Cache port's start includes
// loading its data file.
func resultStages(engine string) []string {
	if engine == engineCache {
		return []string{stageUnpack, stageRestore, stageStart}
	}
	return []string{stageUnpack, stageRestore, stageParse, stageDecode, stageApply}
}

// Engines as the summaries name them.
const (
	enginePlus  = "tendisplus"
	engineSSD   = "tendisssd"
	engineCache = "cache"
)

// Port outcomes in the result table.
const (
	portPending = "notrun"
	portDone    = "done"
	portSkipped = "skip"
	portFailed  = "failed"
)

// detailFileName is the per-port file, beside the downloads, that holds what the node log leaves
// out: a line per binlog and each kvstore's stage CPU. It outlives the port.
const detailFileName = "rollback_detail_%d.log"

type portReport struct {
	inst InstanceRestore
	now  func() time.Time

	mu        sync.Mutex
	status    string
	err       error
	durations map[string]time.Duration
	// cpu is the CPU time of a stage's child processes; next to the wall time it tells a slow
	// tool from one waiting for a core.
	cpu     map[string]time.Duration
	binlogs int
	replies replyStats
	// seenKinds are the kinds of error reply already logged; later ones are only counted.
	seenKinds map[string]bool
	// kvstores holds each Tendisplus kvstore's replay; port totals above include them.
	kvstores map[int]*kvstoreReport
	// instanceCPU is the instance process's CPU over the replay, -1 when it could not be read.
	instanceCPU time.Duration
	// restored tells how restorebackup placed the unpacked backup: moved or copied.
	restored string
	// gaps lists the binlog indexes the plan let the replay skip, e.g. "kv3 #31-33".
	gaps []string
	// heartbeat is a TendisSSD port's source heartbeat after the restore, zero when none was read;
	// beatDBSize is the source dbsize dbmon wrote beside it, -1 without one.
	heartbeat  time.Time
	beatDBSize int64
	// beatWarn tells why the source heartbeat is off recover_at or was not read; it never fails
	// the port.
	beatWarn string
	prog     portProgress
	ssd      *ssdReplayReport
	cache    *cacheLoadReport

	detailMu   sync.Mutex
	detailPath string
	detailFile *os.File
	// detailReplies counts the error replies offered to the detail file, written or not.
	detailReplies int
}

// kvstoreReport is one kvstore's binlog replay.
type kvstoreReport struct {
	files     int
	writes    int
	posBefore uint64
	// lastSent is the last binlog id the planned binlogs held up to recover_at, where binlogpos
	// must end; posAfter is the binlogpos read after the replay, when posRead.
	lastSent uint64
	posAfter uint64
	posRead  bool
	// heartbeat is the source heartbeat the kvstore held after the replay, zero when none was read.
	heartbeat time.Time
	durations map[string]time.Duration
	cpu       map[string]time.Duration
}

// ssdReplayReport is where a TendisSSD port's replay started and how far it went.
type ssdReplayReport struct {
	// restoredSeq is the restored instance's end seq, 0 when binlogsize could not tell; nameSeq is
	// the one in the full backup's name, 0 when the name holds none.
	restoredSeq uint64
	nameSeq     uint64
	startSeq    uint64
	// from is what the start follows: the restored end seq or the backup name's.
	from     string
	endMs    int64
	firstSeq int64
	lastSeq  int64
	lastFile string
}

// cacheLoadReport is a Cache port's instance once loaded.
type cacheLoadReport struct {
	aof    bool
	empty  bool
	dbsize int64
	rss    int64
}

// addKvstore books wall and CPU time of a kvstore's stage, on the kvstore and its port.
func (p *portReport) addKvstore(kvstore int, stage string, wall, cpu time.Duration) {
	p.mu.Lock()
	defer p.mu.Unlock()
	k := p.kvstoreLocked(kvstore)
	if wall > 0 {
		k.durations[stage] += wall
		p.durations[stage] += wall
	}
	if cpu > 0 {
		k.cpu[stage] += cpu
		p.cpu[stage] += cpu
	}
}

// kvstoreReplayed records a kvstore's outcome; lastSent is where it stopped, on failure too.
func (p *portReport) kvstoreReplayed(kvstore, files, writes int, posBefore, lastSent uint64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	k := p.kvstoreLocked(kvstore)
	k.files, k.writes, k.posBefore, k.lastSent = files, writes, posBefore, lastSent
}

func (p *portReport) kvstoreAfter(kvstore int, pos uint64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	k := p.kvstoreLocked(kvstore)
	k.posAfter, k.posRead = pos, true
}

func (p *portReport) kvstoreHeartbeat(kvstore int, beat time.Time) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.kvstoreLocked(kvstore).heartbeat = beat
}

func (p *portReport) setHeartbeat(beat time.Time, dbsize int64) {
	p.mu.Lock()
	p.heartbeat, p.beatDBSize = beat, dbsize
	p.mu.Unlock()
}

// heartbeatOff logs a heartbeat warning and keeps it for the port's diag.
func (p *portReport) heartbeatOff(log portLog, format string, args ...interface{}) {
	msg := fmt.Sprintf(format, args...)
	log.Warn("%s", msg)
	p.mu.Lock()
	p.beatWarn = msg
	p.mu.Unlock()
}

// allowedGaps records binlog indexes skipped as the plan allowed; label tells the chain apart.
func (p *portReport) allowedGaps(label string, missing []int64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.gaps = append(p.gaps, label+indexRanges(missing))
}

func (p *portReport) kvstoreLocked(kvstore int) *kvstoreReport {
	if p.kvstores == nil {
		p.kvstores = map[int]*kvstoreReport{}
	}
	k := p.kvstores[kvstore]
	if k == nil {
		k = &kvstoreReport{durations: map[string]time.Duration{}, cpu: map[string]time.Duration{}}
		p.kvstores[kvstore] = k
	}
	return k
}

func (p *portReport) sortedKvstores() []int {
	kvstores := make([]int, 0, len(p.kvstores))
	for kvstore := range p.kvstores {
		kvstores = append(kvstores, kvstore)
	}
	sort.Ints(kvstores)
	return kvstores
}

// slowKvstores names the kvstores whose replay took over twice the port's median and a minute
// more, the only kvstores the node log tells about when nothing failed.
func (p *portReport) slowKvstores() []string {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.kvstores) < 3 {
		return nil
	}
	walls := map[int]time.Duration{}
	var sorted []time.Duration
	for kvstore, k := range p.kvstores {
		for _, d := range k.durations {
			walls[kvstore] += d
		}
		sorted = append(sorted, walls[kvstore])
	}
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	median := sorted[len(sorted)/2]
	var slow []string
	for _, kvstore := range p.sortedKvstores() {
		if w := walls[kvstore]; w > 2*median && w-median > time.Minute {
			slow = append(slow, fmt.Sprintf("kv%d %s", kvstore, shortDuration(w)))
		}
	}
	if len(slow) > 0 {
		slow = append(slow, "median "+shortDuration(median))
	}
	return slow
}

// firstReply tells whether this is the port's first error reply of its kind, the only one the
// node log shows; the rest are counted in the summary.
func (p *portReport) firstReply(kind string) bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.seenKinds[kind] {
		return false
	}
	if p.seenKinds == nil {
		p.seenKinds = map[string]bool{}
	}
	p.seenKinds[kind] = true
	return true
}

func (p *portReport) setInstanceCPU(d time.Duration) {
	p.mu.Lock()
	p.instanceCPU = d
	p.mu.Unlock()
}

func (p *portReport) setRestored(how string) {
	p.mu.Lock()
	p.restored = how
	p.mu.Unlock()
}

func (p *portReport) restoredHow() string {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.restored
}

func (p *portReport) setSSD(s ssdReplayReport) {
	p.mu.Lock()
	p.ssd = &s
	p.mu.Unlock()
}

func (p *portReport) setCacheLoaded(c cacheLoadReport) {
	p.mu.Lock()
	p.cache = &c
	p.mu.Unlock()
}

func (p *portReport) add(stage string, d time.Duration) {
	p.mu.Lock()
	p.durations[stage] += d
	p.mu.Unlock()
}

func (p *portReport) duration(stage string) time.Duration {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.durations[stage]
}

func (p *portReport) addCPU(stage string, d time.Duration) {
	if d <= 0 {
		return
	}
	p.mu.Lock()
	p.cpu[stage] += d
	p.mu.Unlock()
}

// timed runs fn and books its duration under stage.
func (p *portReport) timed(stage string, fn func() error) error {
	start := time.Now()
	err := fn()
	p.add(stage, time.Since(start))
	return err
}

func (p *portReport) replayed(binlogs int, stats replyStats) {
	p.mu.Lock()
	p.binlogs = binlogs
	p.replies = stats
	p.mu.Unlock()
}

func (p *portReport) finish(err error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if err != nil {
		p.status, p.err = portFailed, err
		p.prog.phase = phaseFailed
		return
	}
	p.status = portDone
	p.prog.phase = phaseDone
}

// detail appends a line to the port's detail file, opened on the first line of this attempt.
// The file is a convenience: failing to write it fails nothing.
func (p *portReport) detail(format string, args ...interface{}) {
	p.detailMu.Lock()
	defer p.detailMu.Unlock()
	if p.detailPath == "" {
		return
	}
	if p.detailFile == nil {
		f, err := os.OpenFile(p.detailPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		if err != nil {
			logWarn("[%d] detail file %s not written: %v", p.inst.DestPort, p.detailPath, err)
			p.detailPath = ""
			return
		}
		p.detailFile = f
		_, _ = fmt.Fprintf(f, "# attempt %s\n", p.now().Format(time.RFC3339))
	}
	_, _ = fmt.Fprintf(p.detailFile, format+"\n", args...)
}

// detailMaxReplies caps the error replies a port writes to its detail file, so a replay answering
// millions of commands with errors cannot fill the disk; the summary still counts every one.
const detailMaxReplies = 1000

// detailReply writes an error reply to the detail file, the port's first detailMaxReplies only.
func (p *portReport) detailReply(format string, args ...interface{}) {
	p.detailMu.Lock()
	p.detailReplies++
	n := p.detailReplies
	p.detailMu.Unlock()
	if n <= detailMaxReplies {
		p.detail(format, args...)
	}
}

// noteOmittedReplies tells in the detail file how many error replies detailReply left out.
func (p *portReport) noteOmittedReplies() {
	p.detailMu.Lock()
	n := p.detailReplies - detailMaxReplies
	p.detailMu.Unlock()
	if n > 0 {
		p.detail("... (%d more error replies omitted)", n)
	}
}

// closeDetail closes the detail file and returns its path, empty when nothing was written.
func (p *portReport) closeDetail() string {
	p.detailMu.Lock()
	defer p.detailMu.Unlock()
	if p.detailFile == nil {
		return ""
	}
	_ = p.detailFile.Close()
	p.detailFile = nil
	return p.detailPath
}

// hostReport collects one node's ports for the summaries printed when it starts and ends.
type hostReport struct {
	destIP    string
	engine    string
	recoverAt string
	// tuning is the temp instance directives written for the replay, e.g. rocks.write_buffer_size=...
	tuning string
	ports  []*portReport
	byPort map[int]*portReport
	// selfCPU is the actuator's own CPU when the node started, its client side of every stage.
	selfCPU time.Duration
	// workload sizes the snapshot cadence: the planned binlog bytes, or a quarter of the full
	// backups when there are none.
	workload int64
	started  time.Time
	// now is replaced in tests, which drive the progress snapshots on a fake clock.
	now func() time.Time
}

func newHostReport(destIP, engine string, instances []InstanceRestore) *hostReport {
	h := &hostReport{destIP: destIP, engine: engine, byPort: map[int]*portReport{}, selfCPU: selfCPU(),
		now: time.Now}
	h.started = h.now()
	for _, inst := range instances {
		p := &portReport{inst: inst, status: portPending, durations: map[string]time.Duration{},
			cpu: map[string]time.Duration{}, instanceCPU: -1, beatDBSize: -1,
			now: func() time.Time { return h.now() }}
		h.ports = append(h.ports, p)
		h.byPort[inst.DestPort] = p
	}
	sort.Slice(h.ports, func(i, j int) bool { return h.ports[i].inst.DestPort < h.ports[j].inst.DestPort })
	return h
}

// newReport is the job's host report, keeping each port's detail file beside the downloads.
func (j Job) newReport(engine string) *hostReport {
	h := newHostReport(j.DestIP, engine, j.Instances)
	h.recoverAt = j.RecoverAt
	if j.SaveDir != "" {
		for _, p := range h.ports {
			p.detailPath = filepath.Join(j.SaveDir, fmt.Sprintf(detailFileName, p.inst.DestPort))
		}
	}
	return h
}

func (h *hostReport) port(destPort int) *portReport {
	return h.byPort[destPort]
}

func (h *hostReport) skipped(destPort int) {
	p := h.port(destPort)
	p.mu.Lock()
	p.status, p.prog.phase = portSkipped, phaseSkipped
	p.mu.Unlock()
}

// portPlan is what the opening summary shows for one port.
type portPlan struct {
	fullBytes   int64
	binlogs     int
	binlogBytes int64
	memory      int64
}

// logPlan prints the opening summary: which shard and source each port restores and how much, the
// limits it runs under, the tuning and the memory and disk it is expected to take. replay tells
// how many replay at once.
//
//	RedisRollback plan tendisplus: 6 ports, 1 skipped
//	 port  shard          source                  full binlogs         memory
//	30000  0-104999       1.1.1.1:30000           4.8G  360 (6.5G)       3.1G
//	 limits: cpu=16 unpack=8 loading=16 mem_available=120.5GiB max_concurrency=0
func (h *hostReport) logPlan(limits Limits, plans map[int]portPlan, unpackDir, replay string) {
	var memory, download, unpack, binlogBytes int64
	var rows []string
	var skipped []int
	for _, p := range h.ports {
		if p.status == portSkipped {
			skipped = append(skipped, p.inst.DestPort)
			continue
		}
		plan := plans[p.inst.DestPort]
		memory += plan.memory
		download += plan.fullBytes + plan.binlogBytes
		unpack += plan.fullBytes
		binlogBytes += plan.binlogBytes
		binlogs := "-"
		if plan.binlogs > 0 {
			binlogs = fmt.Sprintf("%d (%s)", plan.binlogs, shortBytes(plan.binlogBytes))
		}
		rows = append(rows, fmt.Sprintf("%5d  %-13s  %-21s %6s %-12s %7s", p.inst.DestPort,
			clip(p.inst.ShardValue, 13), clip(fmt.Sprintf("%s:%d", p.inst.SourceIP, p.inst.SourcePort), 21),
			shortBytes(plan.fullBytes), binlogs, shortBytes(plan.memory)))
	}
	h.workload = binlogBytes
	if binlogBytes == 0 {
		h.workload = unpack / 4
	}
	lines := []string{
		fmt.Sprintf("RedisRollback plan %s: %d ports, %d skipped", h.engine, len(h.ports), len(skipped)),
		fmt.Sprintf("%5s  %-13s  %-21s %6s %-12s %7s", "port", "shard", "source", "full", "binlogs", "memory"),
	}
	lines = append(lines, rows...)
	if h.recoverAt != "" {
		lines = append(lines, " recover_at: "+h.recoverAt)
	}
	lines = append(lines, " limits: "+limits.String())
	if replay != "" {
		lines = append(lines, " replay: "+replay)
	}
	if h.tuning != "" {
		lines = append(lines, " tuning: "+h.tuning)
	}
	if len(skipped) > 0 {
		lines = append(lines, " skipped (already done): "+portRanges(skipped))
	}
	lines = append(lines, fmt.Sprintf(" memory~%s, download %s, unpack %s+ into %s", shortBytes(memory),
		shortBytes(download), shortBytes(unpack), unpackDir))
	logInfo("%s", strings.Join(lines, "\n"))
}

// logResult prints the result table and then one diagnosis per port, on success and failure alike.
// Each port's kvstore CPU goes to its detail file first, which is then closed.
func (h *hostReport) logResult() {
	paths := map[int]string{}
	for _, p := range h.ports {
		p.mu.Lock()
		var lines []string
		for _, kvstore := range p.sortedKvstores() {
			k := p.kvstores[kvstore]
			lines = append(lines, fmt.Sprintf("kv=%d binlogs=%d writes=%d %s", kvstore, k.files, k.writes,
				stageText(k.durations, k.cpu)))
		}
		p.mu.Unlock()
		for _, line := range lines {
			p.detail("%s", line)
		}
		paths[p.inst.DestPort] = p.closeDetail()
	}
	logInfo("%s", h.resultText())
	for _, p := range h.ports {
		level := levelInfo
		p.mu.Lock()
		if p.err != nil {
			level = levelError
		} else if p.replies.Errors > p.replies.Expected || p.beatWarn != "" {
			level = levelWarn
		}
		p.mu.Unlock()
		logRecord(level, "%s", h.diagText(p, paths[p.inst.DestPort]))
	}
}

// resultText is one row per port with its status, stage wall times and replay counts; a row
// below it gives each stage's CPU: its child processes', the instance's while it restores or
// applies, and the actuator's own while it decodes or sends batches. err counts the error
// replies needing attention: that port's temp instance may be missing writes.
//
//	RedisRollback result tendisplus: 6/6 done
//	 port  status  unpack restore   parse  decode   apply binlogs   cmds  err
//	30000  done       10s     19s       -      4s   7m46s     360  1.24M    0
//	         cpu       8s     15s     25s      5s  44m10s
//	 wall 9m40s; cpu: actuator 3m30s, instances 45m
func (h *hostReport) resultText() string {
	stages := resultStages(h.engine)
	binlogs := h.engine != engineCache
	cells := func(first, second string, values []string, tail string) string {
		row := fmt.Sprintf("%5s  %-6s", first, second)
		for _, v := range values {
			row += fmt.Sprintf(" %7s", v)
		}
		return strings.TrimRight(row+tail, " ")
	}
	tail := ""
	if binlogs {
		tail = fmt.Sprintf(" %7s %6s %4s", "binlogs", "cmds", "err")
	}
	lines := []string{"", cells("port", "status", stages, tail)}
	byStatus := map[string][]int{}
	var attention []string
	var instanceCPU time.Duration
	sampled := false
	for _, p := range h.ports {
		p.mu.Lock()
		port := p.inst.DestPort
		byStatus[p.status] = append(byStatus[p.status], port)
		walls, cpus := make([]string, len(stages)), make([]string, len(stages))
		hasCPU := false
		for i, s := range stages {
			walls[i], cpus[i] = "-", "-"
			if d, ok := p.durations[s]; ok && d > 0 {
				walls[i] = shortDuration(d)
			}
			if c := p.cpu[s]; c > 0 {
				cpus[i], hasCPU = shortDuration(c), true
			}
		}
		tail = ""
		if binlogs {
			errs := p.replies.Errors - p.replies.Expected
			tail = fmt.Sprintf(" %7d %6s %4d", p.binlogs, shortCount(p.replies.Lines), errs)
			if errs > 0 {
				attention = append(attention, fmt.Sprintf("%d(%d)", port, errs))
			}
		}
		lines = append(lines, cells(fmt.Sprint(port), p.status, walls, tail))
		if hasCPU {
			lines = append(lines, cells("", "  cpu", cpus, ""))
		}
		if p.instanceCPU >= 0 {
			instanceCPU += p.instanceCPU
			sampled = true
		}
		p.mu.Unlock()
	}
	lines[0] = fmt.Sprintf("RedisRollback result %s: %d/%d done", h.engine,
		len(byStatus[portDone])+len(byStatus[portSkipped]), len(h.ports))
	footer := fmt.Sprintf(" wall %s; cpu: actuator %s", shortDuration(h.now().Sub(h.started)),
		shortDuration(selfCPU()-h.selfCPU))
	if sampled {
		footer += ", instances " + shortDuration(instanceCPU)
	}
	lines = append(lines, footer)
	if h.tuning != "" {
		lines = append(lines, " tuning: "+h.tuning)
	}
	for _, s := range []struct{ status, label string }{
		{portFailed, "failed"}, {portSkipped, "skipped (already done)"}, {portPending, "not run"},
	} {
		if ports := byStatus[s.status]; len(ports) > 0 {
			lines = append(lines, fmt.Sprintf(" %s: %s", s.label, portRanges(ports)))
		}
	}
	if len(attention) > 0 {
		lines = append(lines, " replay errors, port(errors): "+strings.Join(attention, " "))
	}
	return strings.Join(lines, "\n")
}

// diagText is everything needed to tell what a port's temp instance holds, without the
// exercise analysis having to read anything but the node log. A Tendisplus port has a row per
// kvstore, a TendisSSD port one for its only stream:
//
//	[30000] diag recover_at 11-05 16:05:00
//	 full backup copied; instance cpu 1m30s
//	  kv   bl       before -> after        heartbeat  parse decode  apply
//	   0   36       391911 -> 392911         16:04:56     3s     4s     6s
//	 detail: /data/dbbak/recover_redis/rollback_detail_30000.log
//
// before and after are binlogpos around the replay; after is ? when it was not read. The replay
// already fails the port when after is not the last binlog id sent, so that id is not shown.
// Error reply samples are cut to one line each.
func (h *hostReport) diagText(p *portReport, detail string) string {
	p.mu.Lock()
	defer p.mu.Unlock()
	port := p.inst.DestPort
	switch p.status {
	case portSkipped:
		return fmt.Sprintf("[%d] diag: skipped, already rolled back", port)
	case portPending:
		return fmt.Sprintf("[%d] diag: not run", port)
	}
	lines := []string{fmt.Sprintf("[%d] diag recover_at %s", port, shortTime(h.recoverAt))}
	var about []string
	if p.restored != "" {
		about = append(about, "full backup "+p.restored)
	}
	if p.instanceCPU >= 0 {
		about = append(about, "instance cpu "+shortDuration(p.instanceCPU))
	}
	if c := p.cache; c != nil {
		if c.empty {
			about = append(about, "no full backup, left empty")
		} else {
			kind := "RDB"
			if c.aof {
				kind = "AOF"
			}
			about = append(about, fmt.Sprintf("backup %s, dbsize %d, rss %s", kind, c.dbsize, shortBytes(c.rss)))
		}
	}
	ssdStream := p.ssd != nil && p.binlogs > 0
	if !p.heartbeat.IsZero() && !ssdStream {
		about = append(about, "heartbeat "+p.heartbeat.Local().Format("15:04:05"))
	}
	if !p.heartbeat.IsZero() && p.beatDBSize >= 0 {
		about = append(about, fmt.Sprintf("source dbsize %d", p.beatDBSize))
	}
	if len(about) > 0 {
		lines = append(lines, " "+strings.Join(about, "; "))
	}
	if s := p.ssd; s != nil {
		lines = append(lines, fmt.Sprintf(" start after seq %d (%s): restored %s, backup name %s",
			s.startSeq-1, s.from, seqText(s.restoredSeq), seqText(s.nameSeq)),
			fmt.Sprintf(" replay end %dms", s.endMs))
	}
	if len(p.gaps) > 0 {
		lines = append(lines, " binlog gaps allowed: "+strings.Join(p.gaps, ", "))
	}
	if len(p.kvstores) > 0 {
		lines = append(lines, fmt.Sprintf("  %3s %4s %12s -> %-12s %9s %6s %6s %6s", "kv", "bl", "before",
			"after", "heartbeat", "parse", "decode", "apply"))
		for _, kvstore := range p.sortedKvstores() {
			k := p.kvstores[kvstore]
			after, beat := "?", "-"
			if k.posRead {
				after = fmt.Sprint(k.posAfter)
			}
			if !k.heartbeat.IsZero() {
				beat = k.heartbeat.Local().Format("15:04:05")
			}
			lines = append(lines, fmt.Sprintf("  %3d %4d %12d -> %-12s %9s %6s %6s %6s", kvstore, k.files,
				k.posBefore, after, beat, stageCell(k, stageParse), stageCell(k, stageDecode),
				stageCell(k, stageApply)))
		}
	}
	if s := p.ssd; ssdStream {
		k := &kvstoreReport{durations: p.durations, cpu: p.cpu}
		beat := "-"
		if !p.heartbeat.IsZero() {
			beat = p.heartbeat.Local().Format("15:04:05")
		}
		lines = append(lines, fmt.Sprintf("  %4s %10s -> %-10s %8s %6s %6s %6s", "bl", "first", "last",
			"heartbeat", "parse", "decode", "apply"),
			fmt.Sprintf("  %4d %10d -> %-10d %8s %6s %6s %6s", p.binlogs, s.firstSeq, s.lastSeq, beat,
				stageCell(k, stageParse), stageCell(k, stageDecode), stageCell(k, stageApply)),
			" last binlog "+s.lastFile)
	}
	if p.beatWarn != "" {
		lines = append(lines, " heartbeat warn: "+p.beatWarn)
	}
	if r := p.replies; r.Errors > 0 {
		kinds := make([]string, 0, len(r.Kinds))
		for kind, n := range r.Kinds {
			kinds = append(kinds, fmt.Sprintf("%s %d", kind, n))
		}
		sort.Strings(kinds)
		lines = append(lines, fmt.Sprintf(" error replies %d of %d (%d expected): %s", r.Errors, r.Lines, r.Expected,
			strings.Join(kinds, ", ")))
		for _, sample := range r.samples() {
			lines = append(lines, clip("  "+strings.ReplaceAll(sample, "\n", " "), lineWidth))
		}
	}
	if p.err != nil {
		lines = append(lines, " failed: "+p.err.Error())
	}
	if detail != "" {
		lines = append(lines, " detail: "+detail)
	}
	return strings.Join(lines, "\n")
}

// stageCell is a stage's wall time, or its CPU for a stage with CPU only, like the decompressor
// running alongside the replay.
func stageCell(k *kvstoreReport, stage string) string {
	if d := k.durations[stage]; d > 0 {
		return shortDuration(d)
	}
	if c := k.cpu[stage]; c > 0 {
		return shortDuration(c)
	}
	return "-"
}

func seqText(seq uint64) string {
	if seq == 0 {
		return "?"
	}
	return fmt.Sprint(seq)
}

// shortTime is recover_at as month, day and time of day, or as given when it does not parse.
func shortTime(recoverAt string) string {
	if recoverAt == "" {
		return "-"
	}
	t, err := time.Parse(time.RFC3339, recoverAt)
	if err != nil {
		return recoverAt
	}
	return t.Local().Format("01-02 15:04:05")
}

// clip cuts s to n characters, the last one marking the cut.
func clip(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n-1]) + "~"
}

// stageText lists stage times in stageOrder for the detail file; a stage with CPU only, like a
// decompressor running alongside the replay, shows just its CPU.
func stageText(durations, cpu map[string]time.Duration) string {
	var stages []string
	for _, s := range stageOrder {
		d, timed := durations[s]
		c := cpu[s]
		switch {
		case timed && c > 0:
			stages = append(stages, fmt.Sprintf("%s=%s(cpu %s)", s, d.Round(time.Second), c.Round(time.Second)))
		case timed:
			stages = append(stages, fmt.Sprintf("%s=%s", s, d.Round(time.Second)))
		case c > 0:
			stages = append(stages, fmt.Sprintf("%s(cpu %s)", s, c.Round(time.Second)))
		}
	}
	return strings.Join(stages, " ")
}

// selfCPU is the user and system time this process has used so far, 0 when unknown.
func selfCPU() time.Duration {
	var ru syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &ru); err != nil {
		return 0
	}
	return time.Duration(ru.Utime.Nano() + ru.Stime.Nano())
}

func totalSize(files []string) int64 {
	var n int64
	for _, f := range files {
		if st, err := os.Stat(f); err == nil {
			n += st.Size()
		}
	}
	return n
}

// keepOutput writes a tool's raw output to the port's work dir and returns its tail for errors,
// so the node log gets a summary rather than the whole output.
func keepOutput(dir, name string, out []byte) string {
	if len(out) == 0 {
		return ""
	}
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, out, 0644); err != nil {
		path = "(not kept: " + err.Error() + ")"
	}
	const tailBytes = 512
	tail := out
	if len(tail) > tailBytes {
		tail = tail[len(tail)-tailBytes:]
	}
	return fmt.Sprintf("%s (full output in %s)", strings.TrimSpace(string(tail)), path)
}
