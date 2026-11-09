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

// Port outcomes in the summary.
const (
	portPending = "not run"
	portDone    = "done"
	portSkipped = "skipped (already done)"
	portFailed  = "failed"
)

type portReport struct {
	inst InstanceRestore

	mu        sync.Mutex
	status    string
	err       error
	durations map[string]time.Duration
	// cpu is the CPU time of a stage's child processes; next to the wall time it tells a slow
	// tool from one waiting for a core.
	cpu     map[string]time.Duration
	binlogs int
	replies replyStats
	// kvstores holds each Tendisplus kvstore's replay; port totals above include them.
	kvstores map[int]*kvstoreReport
	// instanceCPU is the instance process's CPU over the replay, -1 when it could not be read.
	instanceCPU time.Duration
	// tuning is the temp instance directives written for the replay, e.g. rocks.write_buffer_size=...
	tuning string
	// restored tells how restorebackup placed the unpacked backup: moved or copied.
	restored string
	// gaps lists the binlog indexes the plan let the replay skip, e.g. "kv3 #31-33".
	gaps []string
}

// kvstoreReport is one kvstore's binlog replay.
type kvstoreReport struct {
	files     int
	writes    int
	posBefore uint64
	posAfter  uint64
	// heartbeat is the source heartbeat the kvstore held after the replay, zero when none was read.
	heartbeat time.Time
	durations map[string]time.Duration
	cpu       map[string]time.Duration
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

// kvstoreReplayed records a kvstore's outcome; posAfter is where it stopped, on failure too.
func (p *portReport) kvstoreReplayed(kvstore, files, writes int, posBefore, posAfter uint64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	k := p.kvstoreLocked(kvstore)
	k.files, k.writes, k.posBefore, k.posAfter = files, writes, posBefore, posAfter
}

func (p *portReport) kvstoreHeartbeat(kvstore int, beat time.Time) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.kvstoreLocked(kvstore).heartbeat = beat
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

func (p *portReport) setInstanceCPU(d time.Duration) {
	p.mu.Lock()
	p.instanceCPU = d
	p.mu.Unlock()
}

func (p *portReport) setTuning(tuning string) {
	p.mu.Lock()
	p.tuning = tuning
	p.mu.Unlock()
}

func (p *portReport) setRestored(how string) {
	p.mu.Lock()
	p.restored = how
	p.mu.Unlock()
}

func (p *portReport) add(stage string, d time.Duration) {
	p.mu.Lock()
	p.durations[stage] += d
	p.mu.Unlock()
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
		return
	}
	p.status = portDone
}

// hostReport collects one node's ports for the summaries printed when it starts and ends.
type hostReport struct {
	destIP string
	engine string
	ports  []*portReport
	byPort map[int]*portReport
	// selfCPU is the actuator's own CPU when the node started, its client side of every stage.
	selfCPU time.Duration
}

func newHostReport(destIP, engine string, instances []InstanceRestore) *hostReport {
	h := &hostReport{destIP: destIP, engine: engine, byPort: map[int]*portReport{}, selfCPU: selfCPU()}
	for _, inst := range instances {
		p := &portReport{inst: inst, status: portPending, durations: map[string]time.Duration{},
			cpu: map[string]time.Duration{}, instanceCPU: -1}
		h.ports = append(h.ports, p)
		h.byPort[inst.DestPort] = p
	}
	sort.Slice(h.ports, func(i, j int) bool { return h.ports[i].inst.DestPort < h.ports[j].inst.DestPort })
	return h
}

func (h *hostReport) port(destPort int) *portReport {
	return h.byPort[destPort]
}

func (h *hostReport) skipped(destPort int) {
	h.port(destPort).status = portSkipped
}

// portPlan is what the opening summary shows for one port.
type portPlan struct {
	fullBytes   int64
	binlogs     int
	binlogBytes int64
	memory      int64
	tuning      string
}

// logPlan prints the opening summary: what each port restores, the limits it runs under and the
// memory and disk it is expected to take.
func (h *hostReport) logPlan(limits Limits, plans map[int]portPlan, unpackDir string) {
	var memory, download, unpack int64
	var lines []string
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
		line := fmt.Sprintf("  port %d shard=%s src=%s:%d full=%s binlogs=%d (%s) memory~%s",
			p.inst.DestPort, p.inst.ShardValue, p.inst.SourceIP, p.inst.SourcePort, humanBytes(plan.fullBytes),
			plan.binlogs, humanBytes(plan.binlogBytes), humanBytes(plan.memory))
		if plan.tuning != "" {
			line += " tuning: " + plan.tuning
		}
		lines = append(lines, line)
	}
	logInfo("RedisRollback plan dest=%s engine=%s ports=%d to restore=%d skipped (already done)=%v\n"+
		"  limits: %s\n  memory~%s, downloaded %s, unpacking %s of full backups (more once decompressed) into %s\n%s",
		h.destIP, h.engine, len(h.ports), len(lines), skipped, limits, humanBytes(memory), humanBytes(download),
		humanBytes(unpack), unpackDir, strings.Join(lines, "\n"))
}

// logResult prints the closing summary, on success and failure alike.
func (h *hostReport) logResult() {
	logInfo("%s", h.resultText())
}

// resultText lists each port's outcome and stage times. Ports whose replay got replies needing
// attention are listed apart: their temp instance may be missing writes. A Tendisplus port reads:
//
//	port 30000 shard= src=1.1.1.1:30000 done restore=40s parse(cpu 3s) decode=4s(cpu 5s) apply=6s
//	  full backup copied tuning: rocks.write_buffer_size=134217728 instance cpu=1m30s
//	  binlog gaps allowed: kv3 #31-33
//	  kvstore 0 binlogs=36 writes=1000 binlogpos 391911 -> 392911 heartbeat 10-30 16:04:56 parse(cpu 3s) ...
//
// "full backup" is whether restorebackup moved or copied the unpacked checkpoint, tuning is what
// the temp instance ran with, and instance cpu is what it used during the replay, left out when
// its process could not be read. "binlog gaps allowed" are indexes the plan let the replay skip,
// whose writes the temp instance lacks. A kvstore's heartbeat is the source's it held after the
// replay, left out when there was none. The header's actuator cpu is this process's own.
func (h *hostReport) resultText() string {
	var lines []string
	var failed []int
	var attention []string
	counts := map[string]int{}
	for _, p := range h.ports {
		p.mu.Lock()
		counts[p.status]++
		line := fmt.Sprintf("  port %d shard=%s src=%s:%d %s %s", p.inst.DestPort, p.inst.ShardValue,
			p.inst.SourceIP, p.inst.SourcePort, p.status, stageText(p.durations, p.cpu))
		if p.restored != "" {
			line += " full backup " + p.restored
		}
		if p.tuning != "" {
			line += " tuning: " + p.tuning
		}
		if p.instanceCPU >= 0 {
			line += fmt.Sprintf(" instance cpu=%s", p.instanceCPU.Round(time.Second))
		}
		if p.binlogs > 0 {
			line += fmt.Sprintf(" binlogs=%d %s", p.binlogs, p.replies.summary())
			if n := p.replies.Errors - p.replies.Expected; n > 0 {
				attention = append(attention, fmt.Sprintf("%d(%d)", p.inst.DestPort, n))
			}
		}
		if p.err != nil {
			line += fmt.Sprintf(" error: %v", p.err)
			failed = append(failed, p.inst.DestPort)
		}
		lines = append(lines, line)
		if len(p.gaps) > 0 {
			lines = append(lines, "    binlog gaps allowed: "+strings.Join(p.gaps, ", "))
		}
		kvstores := make([]int, 0, len(p.kvstores))
		for kvstore := range p.kvstores {
			kvstores = append(kvstores, kvstore)
		}
		sort.Ints(kvstores)
		for _, kvstore := range kvstores {
			k := p.kvstores[kvstore]
			beat := ""
			if !k.heartbeat.IsZero() {
				beat = " heartbeat " + k.heartbeat.Local().Format("01-02 15:04:05")
			}
			lines = append(lines, fmt.Sprintf("    kvstore %d binlogs=%d writes=%d binlogpos %d -> %d%s %s",
				kvstore, k.files, k.writes, k.posBefore, k.posAfter, beat, stageText(k.durations, k.cpu)))
		}
		p.mu.Unlock()
	}
	return fmt.Sprintf("RedisRollback result dest=%s engine=%s ports=%d done=%d skipped=%d failed=%d not run=%d "+
		"actuator cpu=%s\n%s\n  failed ports: %v\n  ports with replay errors needing attention, port(errors): %v",
		h.destIP, h.engine, len(h.ports), counts[portDone], counts[portSkipped], counts[portFailed],
		counts[portPending], (selfCPU() - h.selfCPU).Round(time.Second), strings.Join(lines, "\n"), failed, attention)
}

// stageText lists stage times in stageOrder; a stage with CPU only, like a decompressor running
// alongside the replay, shows just its CPU.
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
