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
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// portLog prefixes every line with the port it is about, so concurrent ports stay apart in the
// node log, which all of them share.
type portLog struct {
	prefix string
}

func newPortLog(destIP string, inst InstanceRestore) portLog {
	return portLog{prefix: fmt.Sprintf("[dest=%s:%d shard=%s src=%s:%d] ",
		destIP, inst.DestPort, inst.ShardValue, inst.SourceIP, inst.SourcePort)}
}

func (l portLog) Info(format string, args ...interface{}) {
	mylog.Logger.Info(l.prefix+format, args...)
}

func (l portLog) Warn(format string, args ...interface{}) {
	mylog.Logger.Warn(l.prefix+format, args...)
}

func (l portLog) Error(format string, args ...interface{}) {
	mylog.Logger.Error(l.prefix+format, args...)
}

// Stages timed per port in the end-of-node summary.
const (
	stageDownload = "download"
	stageUnpack   = "unpack"
	stageRestore  = "restore"
	stageStart    = "start"
	stageParse    = "parse"
	stageApply    = "apply"
)

var stageOrder = []string{stageDownload, stageUnpack, stageRestore, stageStart, stageParse, stageApply}

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
	binlogs   int
	replies   replyStats
}

func (p *portReport) add(stage string, d time.Duration) {
	p.mu.Lock()
	p.durations[stage] += d
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
}

func newHostReport(destIP, engine string, instances []InstanceRestore) *hostReport {
	h := &hostReport{destIP: destIP, engine: engine, byPort: map[int]*portReport{}}
	for _, inst := range instances {
		p := &portReport{inst: inst, status: portPending, durations: map[string]time.Duration{}}
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
		lines = append(lines, fmt.Sprintf("  port %d shard=%s src=%s:%d full=%s binlogs=%d (%s) memory~%s",
			p.inst.DestPort, p.inst.ShardValue, p.inst.SourceIP, p.inst.SourcePort, humanBytes(plan.fullBytes),
			plan.binlogs, humanBytes(plan.binlogBytes), humanBytes(plan.memory)))
	}
	mylog.Logger.Info("RedisRollback plan dest=%s engine=%s ports=%d to restore=%d skipped (already done)=%v\n"+
		"  limits: %s\n  memory~%s, downloaded %s, unpacking %s of full backups (more once decompressed) into %s\n%s",
		h.destIP, h.engine, len(h.ports), len(lines), skipped, limits, humanBytes(memory), humanBytes(download),
		humanBytes(unpack), unpackDir, strings.Join(lines, "\n"))
}

// logResult prints the closing summary, on success and failure alike.
func (h *hostReport) logResult() {
	mylog.Logger.Info("%s", h.resultText())
}

// resultText lists each port's outcome and stage times. Ports whose replay got replies needing
// attention are listed apart: their temp instance may be missing writes.
func (h *hostReport) resultText() string {
	var lines []string
	var failed []int
	var attention []string
	counts := map[string]int{}
	for _, p := range h.ports {
		p.mu.Lock()
		counts[p.status]++
		var stages []string
		for _, s := range stageOrder {
			if d, ok := p.durations[s]; ok {
				stages = append(stages, fmt.Sprintf("%s=%s", s, d.Round(time.Second)))
			}
		}
		line := fmt.Sprintf("  port %d shard=%s src=%s:%d %s %s", p.inst.DestPort, p.inst.ShardValue,
			p.inst.SourceIP, p.inst.SourcePort, p.status, strings.Join(stages, " "))
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
		p.mu.Unlock()
		lines = append(lines, line)
	}
	return fmt.Sprintf("RedisRollback result dest=%s engine=%s ports=%d done=%d skipped=%d failed=%d not run=%d\n%s\n"+
		"  failed ports: %v\n  ports with replay errors needing attention, port(errors): %v",
		h.destIP, h.engine, len(h.ports), counts[portDone], counts[portSkipped], counts[portFailed],
		counts[portPending], strings.Join(lines, "\n"), failed, attention)
}

// downloadSpan approximates how long the backup system took to land a port's files, from the
// earliest to the latest modification time; the download node has the exact figures.
func downloadSpan(files []string) time.Duration {
	var first, last time.Time
	for _, f := range files {
		st, err := os.Stat(f)
		if err != nil {
			continue
		}
		if first.IsZero() || st.ModTime().Before(first) {
			first = st.ModTime()
		}
		if st.ModTime().After(last) {
			last = st.ModTime()
		}
	}
	return last.Sub(first)
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
