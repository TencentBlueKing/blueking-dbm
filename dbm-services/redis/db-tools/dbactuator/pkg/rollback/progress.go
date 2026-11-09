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
	"math"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Phases a port shows in the progress snapshot. The ones with a row are under way; the others
// are merged into one line each.
const (
	phaseQueued  = ""
	phaseWaiting = "waiting"
	phaseUnpack  = "unpack"
	phaseRestore = "restore"
	phaseStart   = "start"
	phaseLoad    = "load"
	phaseReplay  = "replay"
	phaseDone    = "done"
	phaseFailed  = "failed"
	phaseSkipped = "skipped"
)

// Units of a phase's progress: bytes read, or a percentage in hundredths as Cache loading gives it.
const (
	unitBytes   = "bytes"
	unitPercent = "percent"
)

// Snapshot cadence: progressTick is how often ports are sampled, shortened in tests; a snapshot
// goes out every progressByteInterval and is skipped while nothing moves, though never for longer
// than progressMaxGap.
var progressTick = 10 * time.Second

const (
	progressMaxGap  = 10 * time.Minute
	progressMinMove = 0.05
	stallAfter      = 2 * time.Minute
	rateWindow      = time.Minute
	etaMinElapsed   = 30 * time.Second
	etaMinFraction  = 0.02
)

// A replaying Tendisplus port lists its kvstores on every kvDetailEvery-th snapshot, and on any
// snapshot where it is stalled or its kvstores are kvSkewDetail or more apart.
const (
	kvDetailEvery = 3
	kvSkewDetail  = 0.40
)

// progressByteInterval grows with the host's workload: 30s under 20G, 1m under 80G, 2m under 150G,
// 3m under 250G, then 5m.
func progressByteInterval(workload int64) time.Duration {
	switch {
	case workload < 20<<30:
		return 30 * time.Second
	case workload < 80<<30:
		return time.Minute
	case workload < 150<<30:
		return 2 * time.Minute
	case workload < 250<<30:
		return 3 * time.Minute
	default:
		return 5 * time.Minute
	}
}

// States of a Tendisplus kvstore in its port's replay.
const (
	kvWaiting = "waiting"
	kvReplay  = "replay"
	kvDone    = "done"
)

func activePhase(phase string) bool {
	switch phase {
	case phaseUnpack, phaseRestore, phaseStart, phaseLoad, phaseReplay:
		return true
	}
	return false
}

type progressSample struct {
	at   time.Time
	done int64
}

// portProgress is where a port is. A phase with no total has no progress signal, e.g. rocksdb
// rebuilding or restorebackup, and only shows how long it has run.
type portProgress struct {
	phase string
	since time.Time
	// wait is what a waiting port waits for, e.g. "replay slots".
	wait        string
	done, total int64
	unit        string
	files       int
	filesTotal  int
	kvDone      int
	kvTotal     int
	// kvstores is each Tendisplus kvstore's share of the replay, by kvstore index.
	kvstores []kvProgress
	// eta is the engine's own estimate, as Cache loading reports it; 0 when it gives none.
	eta     time.Duration
	changed time.Time
	samples []progressSample
	stalled bool
}

// kvProgress is one kvstore's replay, in compressed binlog bytes and files.
type kvProgress struct {
	kvstore           int
	state             string
	done, total       int64
	files, filesTotal int
}

// kvProgressOf seeds each kvstore of chains as waiting, by kvstore index.
func kvProgressOf(chains map[int][]string) []kvProgress {
	kvs := make([]kvProgress, 0, len(chains))
	for kvstore, chain := range chains {
		kvs = append(kvs, kvProgress{kvstore: kvstore, state: kvWaiting, total: totalSize(chain),
			filesTotal: len(chain)})
	}
	sort.Slice(kvs, func(i, j int) bool { return kvs[i].kvstore < kvs[j].kvstore })
	return kvs
}

func (g portProgress) fraction() float64 {
	if g.total <= 0 {
		return 0
	}
	f := float64(g.done) / float64(g.total)
	if f > 1 {
		return 1
	}
	return f
}

// enter starts a phase; total 0 has no progress signal.
func (p *portReport) enter(phase string, total int64, unit string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	now := p.now()
	p.prog = portProgress{phase: phase, since: now, changed: now, total: total, unit: unit}
}

func (p *portReport) waiting(reason string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	now := p.now()
	p.prog = portProgress{phase: phaseWaiting, wait: reason, since: now, changed: now}
}

// enterReplay starts the binlog replay: progress is in compressed binlog bytes, with files and,
// for Tendisplus, kvstores counted beside it.
func (p *portReport) enterReplay(files int, bytes int64, kvstores []kvProgress) {
	p.enter(phaseReplay, bytes, unitBytes)
	p.mu.Lock()
	p.prog.filesTotal, p.prog.kvTotal, p.prog.kvstores = files, len(kvstores), kvstores
	p.mu.Unlock()
}

// kvLocked is kvstore's replay progress, nil when the replay does not track it.
func (p *portReport) kvLocked(kvstore int) *kvProgress {
	for i := range p.prog.kvstores {
		if p.prog.kvstores[i].kvstore == kvstore {
			return &p.prog.kvstores[i]
		}
	}
	return nil
}

func (p *portReport) kvstoreStarted(kvstore int) {
	p.mu.Lock()
	if k := p.kvLocked(kvstore); k != nil {
		k.state = kvReplay
	}
	p.mu.Unlock()
}

func (p *portReport) progressed(n int64) {
	if n <= 0 {
		return
	}
	p.mu.Lock()
	p.prog.done += n
	p.prog.changed, p.prog.stalled = p.now(), false
	p.mu.Unlock()
}

func (p *portReport) binlogReplayed(bytes int64) {
	p.mu.Lock()
	p.binlogReplayedLocked(bytes)
	p.mu.Unlock()
}

func (p *portReport) binlogReplayedLocked(bytes int64) {
	p.prog.files++
	p.prog.done += bytes
	p.prog.changed, p.prog.stalled = p.now(), false
}

// kvstoreBinlogReplayed counts a binlog on kvstore and its port.
func (p *portReport) kvstoreBinlogReplayed(kvstore int, bytes int64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.binlogReplayedLocked(bytes)
	if k := p.kvLocked(kvstore); k != nil {
		k.files++
		k.done += bytes
	}
}

func (p *portReport) kvstoreFinished(kvstore int) {
	p.mu.Lock()
	p.prog.kvDone++
	if k := p.kvLocked(kvstore); k != nil {
		k.state = kvDone
	}
	p.mu.Unlock()
}

// loading records a Cache load at perc percent, with the instance's own eta.
func (p *portReport) loading(perc float64, eta time.Duration) {
	p.mu.Lock()
	defer p.mu.Unlock()
	done := int64(perc * 100)
	if p.prog.unit != unitPercent {
		p.prog.unit, p.prog.total = unitPercent, 100*100
	}
	if done != p.prog.done {
		p.prog.done, p.prog.changed, p.prog.stalled = done, p.now(), false
	}
	p.prog.eta = eta
}

// snapshotter decides when the host's progress goes out and renders it.
type snapshotter struct {
	h     *hostReport
	start time.Time
	last  time.Time
	// shown is each port's phase and fraction in the last snapshot.
	shown map[int]shownProgress
	// replayShots is how many snapshots each port has had in its replay.
	replayShots map[int]int
}

type shownProgress struct {
	phase    string
	fraction float64
}

func newSnapshotter(h *hostReport, start time.Time) *snapshotter {
	return &snapshotter{h: h, start: start, last: start, shown: map[int]shownProgress{},
		replayShots: map[int]int{}}
}

// step samples every port at now and returns the snapshot when one is due, and a warning for
// each port that just stalled.
func (s *snapshotter) step(now time.Time) (string, []string) {
	var warnings []string
	moved := false
	for _, p := range s.h.ports {
		p.mu.Lock()
		g := &p.prog
		if activePhase(g.phase) {
			g.samples = append(g.samples, progressSample{at: now, done: g.done})
			for len(g.samples) > 1 && now.Sub(g.samples[0].at) > rateWindow {
				g.samples = g.samples[1:]
			}
			if g.total > 0 && g.done < g.total && !g.stalled && now.Sub(g.changed) >= stallAfter {
				g.stalled = true
				warnings = append(warnings, fmt.Sprintf("[%d] stalled: %s made no progress in %s",
					p.inst.DestPort, g.phase, shortDuration(now.Sub(g.changed))))
			}
		}
		was, ok := s.shown[p.inst.DestPort]
		if !ok || was.phase != g.phase || abs(g.fraction()-was.fraction) >= progressMinMove {
			moved = true
		}
		p.mu.Unlock()
	}
	since := now.Sub(s.last)
	if since < progressByteInterval(s.h.workload) || !moved && len(warnings) == 0 && since < progressMaxGap {
		return "", warnings
	}
	s.last = now
	return s.render(now), warnings
}

func abs(f float64) float64 {
	if f < 0 {
		return -f
	}
	return f
}

// render is one record for the whole host, so the ports' rows never interleave; a replaying
// Tendisplus port lists its kvstores only when kvDetailed says so:
//
//	RedisRollback progress 14m: 12/20 done
//	 port  phase    progress         done/total       rate     eta
//	30012  replay   ████████░░  81%  292/360 bl     41.0M/s     52s  kv 7/10
//	  kv00          ██████████ 100%  36/36 bl      done
//	  kv01          ██████░░░░  62%  22/36 bl      replay
//	30013  restore                   for 3m10s
//	 done: 30000-30011
//	 waiting: 30016-30019 (replay slots)
func (s *snapshotter) render(now time.Time) string {
	var rows []string
	merged := map[string][]int{}
	var order []string
	add := func(label string, port int) {
		if _, ok := merged[label]; !ok {
			order = append(order, label)
		}
		merged[label] = append(merged[label], port)
	}
	done := 0
	for _, p := range s.h.ports {
		p.mu.Lock()
		g := p.prog
		s.shown[p.inst.DestPort] = shownProgress{phase: g.phase, fraction: g.fraction()}
		port := p.inst.DestPort
		switch {
		case activePhase(g.phase):
			rows = append(rows, progressRow(port, g, now))
			if s.kvDetailed(port, g) {
				for _, k := range g.kvstores {
					rows = append(rows, kvProgressRow(k))
				}
			}
		case g.phase == phaseDone:
			done++
			add("done", port)
		case g.phase == phaseSkipped:
			done++
			add("skipped", port)
		case g.phase == phaseFailed:
			add("failed", port)
		case g.phase == phaseWaiting:
			add("waiting ("+g.wait+")", port)
		default:
			add("queued", port)
		}
		p.mu.Unlock()
	}
	lines := []string{fmt.Sprintf("RedisRollback progress %s: %d/%d done",
		shortDuration(now.Sub(s.start)), done, len(s.h.ports))}
	if len(rows) > 0 {
		lines = append(lines, fmt.Sprintf("%5s  %-7s  %-15s  %-13s %8s %7s", "port", "phase", "progress",
			"done/total", "rate", "eta"))
		lines = append(lines, rows...)
	}
	for _, label := range order {
		lines = append(lines, fmt.Sprintf(" %s: %s", label, portRanges(merged[label])))
	}
	return strings.Join(lines, "\n")
}

// kvDetailed tells whether this snapshot lists port's kvstores under its row: on its first
// snapshot in the replay and every kvDetailEvery-th after it, or whenever it is stalled or skewed.
func (s *snapshotter) kvDetailed(port int, g portProgress) bool {
	if len(g.kvstores) == 0 || g.phase != phaseReplay {
		delete(s.replayShots, port)
		return false
	}
	n := s.replayShots[port]
	s.replayShots[port] = n + 1
	return n%kvDetailEvery == 0 || g.stalled || kvSkew(g.kvstores) >= kvSkewDetail
}

// kvSkew is how far the kvstores still replaying trail the furthest one, 0 when none replays.
func kvSkew(kvs []kvProgress) float64 {
	most, least, active := 0.0, 1.0, false
	for _, k := range kvs {
		f := k.fraction()
		most = math.Max(most, f)
		if k.state == kvReplay {
			least, active = math.Min(least, f), true
		}
	}
	if !active {
		return 0
	}
	return most - least
}

func (k kvProgress) fraction() float64 {
	if k.total <= 0 {
		return 0
	}
	return math.Min(float64(k.done)/float64(k.total), 1)
}

func progressRow(port int, g portProgress, now time.Time) string {
	var bar, amount, rate, eta string
	if g.total > 0 {
		f := g.fraction()
		bar = progressBar(f)
		switch {
		case g.phase == phaseReplay:
			amount = fmt.Sprintf("%d/%d bl", g.files, g.filesTotal)
		case g.unit == unitBytes:
			amount = shortBytes(g.done) + "/" + shortBytes(g.total)
		}
		r := g.rate()
		if g.unit == unitBytes && r > 0 {
			rate = shortBytes(int64(r)) + "/s"
		}
		switch {
		case g.stalled:
			eta = "stalled"
		case now.Sub(g.since) < etaMinElapsed || f < etaMinFraction:
		case g.eta > 0:
			eta = shortDuration(g.eta)
		case r > 0:
			eta = shortDuration(time.Duration(float64(g.total-g.done) / r * float64(time.Second)))
		}
	} else {
		amount = "for " + shortDuration(now.Sub(g.since))
	}
	row := fmt.Sprintf("%5d  %-7s  %-15s  %-13s %8s %7s", port, g.phase, bar, amount, rate, eta)
	if g.kvTotal > 0 {
		row += fmt.Sprintf("  kv %d/%d", g.kvDone, g.kvTotal)
	}
	return strings.TrimRight(row, " ")
}

// progressBar is ten cells and a percentage, e.g. "████████░░  81%".
func progressBar(f float64) string {
	n := int(f * 10)
	return fmt.Sprintf("%s%s %3d%%", strings.Repeat("█", n), strings.Repeat("░", 10-n), int(f*100))
}

// kvProgressRow is a kvstore under its port's row, its bar in the port's progress column.
func kvProgressRow(k kvProgress) string {
	amount := fmt.Sprintf("%d/%d bl", k.files, k.filesTotal)
	return fmt.Sprintf("  kv%02d%10s%-15s  %-13s %s", k.kvstore, "", progressBar(k.fraction()), amount, k.state)
}

// rate is progress per second over the samples of the last rateWindow.
func (g portProgress) rate() float64 {
	if len(g.samples) < 2 {
		return 0
	}
	first, last := g.samples[0], g.samples[len(g.samples)-1]
	secs := last.at.Sub(first.at).Seconds()
	if secs <= 0 {
		return 0
	}
	return float64(last.done-first.done) / secs
}

// trackProgress samples the host until the returned stop is called, logging snapshots as they
// fall due. Snapshots are left out of rollback-exercise analysis.
func (h *hostReport) trackProgress() (stop func()) {
	s := newSnapshotter(h, h.now())
	quit, finished := make(chan struct{}), make(chan struct{})
	go func() {
		defer close(finished)
		ticker := time.NewTicker(progressTick)
		defer ticker.Stop()
		for {
			select {
			case <-quit:
				return
			case <-ticker.C:
				text, warnings := s.step(h.now())
				for _, w := range warnings {
					logWarn("%s", w)
				}
				if text != "" {
					logRecord(levelProgress, "%s", text)
				}
			}
		}
	}()
	return func() {
		close(quit)
		<-finished
	}
}

// portRanges writes ports as runs, e.g. 30000-30011,30013.
func portRanges(ports []int) string {
	sort.Ints(ports)
	var runs []string
	for i := 0; i < len(ports); {
		j := i
		for j+1 < len(ports) && ports[j+1] == ports[j]+1 {
			j++
		}
		if i == j {
			runs = append(runs, strconv.Itoa(ports[i]))
		} else {
			runs = append(runs, fmt.Sprintf("%d-%d", ports[i], ports[j]))
		}
		i = j + 1
	}
	return strings.Join(runs, ",")
}

// shortDuration fits a table cell: 52s, 7m46s, 1h02m.
func shortDuration(d time.Duration) string {
	d = d.Round(time.Second)
	switch {
	case d < time.Minute:
		return fmt.Sprintf("%ds", int(d.Seconds()))
	case d < time.Hour:
		return fmt.Sprintf("%dm%02ds", int(d.Minutes()), int(d.Seconds())%60)
	default:
		return fmt.Sprintf("%dh%02dm", int(d.Hours()), int(d.Minutes())%60)
	}
}

// shortBytes fits a table cell: 812K, 1.4G.
func shortBytes(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%dB", n)
	}
	div, exp := int64(unit), 0
	for m := n / unit; m >= unit; m /= unit {
		div *= unit
		exp++
	}
	v := float64(n) / float64(div)
	if v >= 100 {
		return fmt.Sprintf("%.0f%c", v, "KMGTPE"[exp])
	}
	return fmt.Sprintf("%.1f%c", v, "KMGTPE"[exp])
}

// shortCount fits a table cell: 980, 12.4K, 1.24M.
func shortCount(n int) string {
	switch {
	case n < 1000:
		return strconv.Itoa(n)
	case n < 1000000:
		return fmt.Sprintf("%.1fK", float64(n)/1e3)
	default:
		return fmt.Sprintf("%.2fM", float64(n)/1e6)
	}
}
