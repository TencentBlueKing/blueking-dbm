// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

type logEntry struct {
	level string
	msg   string
}

func assertNodeLogWidths(t *testing.T, entries []logEntry) {
	t.Helper()
	for _, e := range entries {
		for i, line := range strings.Split(e.msg, "\n") {
			width := lineWidth
			if i == 0 {
				width = headWidth
			}
			if n := len([]rune(line)); n > width {
				t.Fatalf("line %d is %d wide, over %d:\n%s", i, n, width, e.msg)
			}
		}
	}
}

func TestWrapRecordBreaksAtSpacesAndCutsLongWords(t *testing.T) {
	got := wrapRecord("[30000] failed: restore rocksdb from /data1/recover_redis/30000/backup failed: " +
		strings.Repeat("x", 100) + "\nshort\n" + strings.Repeat("y ", 50))
	assertNodeLogWidths(t, []logEntry{{levelInfo, got}})
	lines := strings.Split(got, "\n")
	if lines[0] != "[30000] failed: restore rocksdb from" || !strings.HasPrefix(lines[1], wrapIndent+"/data1/") {
		t.Fatalf("got:\n%s", got)
	}
	if !strings.Contains(got, "\nshort\n") || strings.Count(got, "x") != 100 {
		t.Fatalf("lost text:\n%s", got)
	}
}

func captureLogs(t *testing.T) func() []logEntry {
	t.Helper()
	var mu sync.Mutex
	var entries []logEntry
	emitLog = func(level, msg string) {
		mu.Lock()
		entries = append(entries, logEntry{level, msg})
		mu.Unlock()
	}
	t.Cleanup(func() { emitLog = emit })
	return func() []logEntry {
		mu.Lock()
		defer mu.Unlock()
		return append([]logEntry{}, entries...)
	}
}

func containsAll(t *testing.T, msg string, parts ...string) {
	t.Helper()
	for _, part := range parts {
		if !strings.Contains(msg, part) {
			t.Fatalf("misses %q:\n%s", part, msg)
		}
	}
}

func TestPlanSummaryMapsPortsToShardsOnce(t *testing.T) {
	logs := captureLogs(t)
	var insts []InstanceRestore
	plans := map[int]portPlan{}
	for i := 0; i < 3; i++ {
		port := 30000 + i
		insts = append(insts, InstanceRestore{DestPort: port, SourceIP: "127.100.100.100", SourcePort: port,
			ShardValue: fmt.Sprintf("%d-%d,%d-%d", i*104999, i*104999+104998, 900000+i, 999999)})
		plans[port] = portPlan{fullBytes: 123 << 30, binlogs: 3600, binlogBytes: 987 << 30, memory: 31 << 30}
	}
	h := newHostReport("127.100.100.100", enginePlus, insts)
	h.recoverAt = "2026-11-05T16:05:00+08:00"
	h.tuning = "rocks.write_buffer_size=134217728"
	h.skipped(30002)
	h.logPlan(Limits{CPU: 16, Unpack: 8, MemAvailable: 64 << 30}, plans, "/data1/recover_redis",
		"10 of 30 kvstores at once")
	assertNodeLogWidths(t, logs())
	containsAll(t, logs()[0].msg,
		"RedisRollback plan tendisplus: 3 ports, 1 skipped",
		" port  shard          source                  full binlogs       memory",
		"30001  104999-20999~  127.100.100.100:30001   123G 3600 (987G)    31.0G",
		" recover_at: 2026-11-05T16:05:00+08:00",
		" limits: cpu=16 unpack=8",
		" replay: 10 of 30 kvstores at once",
		" tuning: rocks.write_buffer_size=134217728",
		" skipped (already done): 30002",
		" memory~62.0G, download 2.2T, unpack 246G+ into /data1/recover_redis",
	)
	if h.workload != 2*987<<30 {
		t.Fatalf("workload %d, want the binlogs of the ports not skipped", h.workload)
	}
}

func TestPlanWorkloadFallsBackToAQuarterOfTheFullBackups(t *testing.T) {
	captureLogs(t)
	h := newHostReport("2.2.2.2", engineCache, []InstanceRestore{{DestPort: 30000}, {DestPort: 30001}})
	h.logPlan(Limits{}, map[int]portPlan{30000: {fullBytes: 40 << 30}, 30001: {fullBytes: 40 << 30}}, "/data1", "")
	if h.workload != 20<<30 || progressByteInterval(h.workload) != time.Minute {
		t.Fatalf("workload %d", h.workload)
	}
}

func TestProgressByteIntervalGrowsWithTheWorkload(t *testing.T) {
	for workload, want := range map[int64]time.Duration{
		0: 30 * time.Second, 20<<30 - 1: 30 * time.Second, 20 << 30: time.Minute, 80<<30 - 1: time.Minute,
		80 << 30: 2 * time.Minute, 150<<30 - 1: 2 * time.Minute, 150 << 30: 3 * time.Minute,
		250<<30 - 1: 3 * time.Minute, 250 << 30: 5 * time.Minute, 4 << 40: 5 * time.Minute,
	} {
		if got := progressByteInterval(workload); got != want {
			t.Fatalf("%d: got %v, want %v", workload, got, want)
		}
	}
}

// clockedHost returns a host whose clock the test advances.
func clockedHost(ports ...int) (*hostReport, *time.Time) {
	var insts []InstanceRestore
	for _, port := range ports {
		insts = append(insts, InstanceRestore{DestPort: port})
	}
	h := newHostReport("2.2.2.2", enginePlus, insts)
	now := time.Date(2026, 11, 5, 10, 0, 0, 0, time.Local)
	h.now, h.started = func() time.Time { return now }, now
	return h, &now
}

// run steps s every progressTick for d and returns when each snapshot went out.
func run(s *snapshotter, now *time.Time, d time.Duration, each func()) []time.Duration {
	var at []time.Duration
	for end := now.Add(d); now.Before(end); {
		*now = now.Add(10 * time.Second)
		if each != nil {
			each()
		}
		if text, _ := s.step(*now); text != "" {
			at = append(at, now.Sub(s.start))
		}
	}
	return at
}

func TestSnapshotCadence(t *testing.T) {
	h, now := clockedHost(30000)
	h.port(30000).enter(phaseRestore, 0, "")
	idle := run(newSnapshotter(h, *now), now, 12*time.Minute, nil)
	want := []time.Duration{30 * time.Second, 10*time.Minute + 30*time.Second}
	if fmt.Sprint(idle) != fmt.Sprint(want) {
		t.Fatalf("idle snapshots at %v, want %v", idle, want)
	}

	h, now = clockedHost(30000)
	h.workload = 80 << 30
	p := h.port(30000)
	p.enter(phaseUnpack, 1<<40, unitBytes)
	s := newSnapshotter(h, *now)
	// 1% per tick stays under the total and clears 5% inside every 2m interval.
	got := run(s, now, 12*time.Minute, func() { p.progressed(int64(1<<40) / 100) })
	if len(got) != 6 || got[0] != 2*time.Minute {
		t.Fatalf("snapshots %v", got)
	}
	for i := 1; i < len(got); i++ {
		if gap := got[i] - got[i-1]; gap != 2*time.Minute {
			t.Fatalf("snapshot at %v came %v after the last, want 2m: %v", got[i], gap, got)
		}
	}
}

// replayingPort is a Tendisplus port replaying kvstores kv00 and kv01, both started.
func replayingPort(h *hostReport, port int) *portReport {
	p := h.port(port)
	p.enterReplay(20, 20<<20, []kvProgress{
		{kvstore: 0, state: kvWaiting, total: 10 << 20, filesTotal: 10},
		{kvstore: 1, state: kvWaiting, total: 10 << 20, filesTotal: 10},
	})
	p.kvstoreStarted(0)
	p.kvstoreStarted(1)
	return p
}

func TestSnapshotListsKvstoresOnTheFirstAndEveryThirdReplaySnapshot(t *testing.T) {
	h, now := clockedHost(30000)
	p := replayingPort(h, 30000)
	s := newSnapshotter(h, *now)
	var detailed []bool
	for i := 0; i < 7; i++ {
		*now = now.Add(10 * time.Second)
		p.kvstoreBinlogReplayed(0, 1<<20)
		p.kvstoreBinlogReplayed(1, 1<<20)
		text := s.render(*now)
		assertNodeLogWidths(t, []logEntry{{levelProgress, text}})
		if !strings.Contains(text, "  kv 0/2") {
			t.Fatalf("port row lost its kvstore count:\n%s", text)
		}
		detailed = append(detailed, strings.Contains(text, "  kv00"))
	}
	if want := "[true false false true false false true]"; fmt.Sprint(detailed) != want {
		t.Fatalf("kvstore rows on snapshots %v, want %s", detailed, want)
	}
}

func TestSnapshotListsKvstoresOfASkewedOrStalledPort(t *testing.T) {
	h, now := clockedHost(30000)
	p := replayingPort(h, 30000)
	s := newSnapshotter(h, *now)
	_ = s.render(*now)
	p.kvstoreBinlogReplayed(0, 4<<20)
	p.kvstoreBinlogReplayed(1, 1<<20)
	if text := s.render(*now); strings.Contains(text, "kv00") {
		t.Fatalf("30%% apart lists kvstores:\n%s", text)
	}
	p.kvstoreBinlogReplayed(0, 2<<20)
	if text := s.render(*now); !strings.Contains(text, "kv00") {
		t.Fatalf("50%% apart leaves kvstores out:\n%s", text)
	}
	p.kvstoreBinlogReplayed(1, 5<<20)
	_ = s.render(*now)
	p.mu.Lock()
	p.prog.stalled = true
	p.mu.Unlock()
	if text := s.render(*now); !strings.Contains(text, "kv00") {
		t.Fatalf("stalled port leaves kvstores out:\n%s", text)
	}
	p.mu.Lock()
	p.prog.stalled = false
	p.mu.Unlock()
	if text := s.render(*now); strings.Contains(text, "kv00") {
		t.Fatalf("even port lists kvstores off cadence:\n%s", text)
	}
}

func TestKvSkewMeasuresReplayingKvstoresFromTheFurthest(t *testing.T) {
	kvs := []kvProgress{
		{state: kvDone, done: 10, total: 10},
		{state: kvReplay, done: 5, total: 10},
		{state: kvWaiting, total: 10},
	}
	if got := kvSkew(kvs); got != 0.5 {
		t.Fatalf("skew %v", got)
	}
	if got := kvSkew(kvs[:1]); got != 0 {
		t.Fatalf("skew with none replaying %v", got)
	}
}

func TestSnapshotMergesPortsAndShowsETAOnceItCan(t *testing.T) {
	h, now := clockedHost(30000, 30001, 30002, 30003, 30004, 30005, 30006, 30007, 30009)
	h.workload = 20 << 30
	for _, port := range []int{30000, 30001, 30002} {
		h.port(port).finish(nil)
	}
	h.skipped(30009)
	h.port(30007).finish(errors.New("x"))
	h.port(30004).waiting("replay slots")
	h.port(30005).waiting("replay slots")
	replay := h.port(30003)
	kvs := make([]kvProgress, 10)
	for i := range kvs {
		kvs[i] = kvProgress{kvstore: i, state: kvWaiting, total: 110 << 20, filesTotal: 1}
	}
	kvs[0].total = 10 << 20
	replay.enterReplay(10, 1000<<20, kvs)
	replay.kvstoreStarted(0)
	replay.kvstoreStarted(1)
	s := newSnapshotter(h, *now)
	tick := func(n int) string {
		var text string
		for i := 0; i < n; i++ {
			*now = now.Add(10 * time.Second)
			text, _ = s.step(*now)
		}
		return text
	}
	if text := tick(1); text != "" {
		t.Fatalf("snapshot before the first interval:\n%s", text)
	}
	replay.kvstoreBinlogReplayed(0, 10<<20)
	replay.kvstoreFinished(0)
	if text := tick(4); text != "" {
		t.Fatalf("snapshot before the first interval:\n%s", text)
	}
	text := tick(1)
	assertNodeLogWidths(t, []logEntry{{levelProgress, text}})
	containsAll(t, text,
		"RedisRollback progress 1m00s: 4/9 done",
		" port  phase    progress         done/total        rate     eta",
		"30003  replay   ░░░░░░░░░░   1%  1/10 bl         205K/s          kv 1/10\n"+
			"  kv00          ██████████ 100%  1/1 bl        done\n"+
			"  kv01          ░░░░░░░░░░   0%  0/1 bl        replay\n"+
			"  kv02          ░░░░░░░░░░   0%  0/1 bl        waiting\n",
		"  kv09          ░░░░░░░░░░   0%  0/1 bl        waiting\n done: 30000-30002",
		" failed: 30007",
		" waiting (replay slots): 30004-30005",
		" queued: 30006",
		" skipped: 30009",
	)
	// 7% done after two minutes: 930MB left at 60MB in the minute sampled, so an ETA appears.
	tick(5)
	replay.kvstoreBinlogReplayed(1, 60<<20)
	text = tick(1)
	containsAll(t, text,
		"30003  replay   ░░░░░░░░░░   7%  2/10 bl         1.0M/s  15m30s  kv 1/10",
		"  kv01          █████░░░░░  54%  1/1 bl        replay",
	)
}

func TestSnapshotLeavesKvstoreRowsOutOnceThePortIsDone(t *testing.T) {
	h, now := clockedHost(30000)
	p := h.port(30000)
	p.enterReplay(1, 1<<20, []kvProgress{{kvstore: 0, state: kvWaiting, total: 1 << 20, filesTotal: 1}})
	p.kvstoreStarted(0)
	p.kvstoreBinlogReplayed(0, 1<<20)
	p.kvstoreFinished(0)
	p.finish(nil)
	*now = now.Add(time.Minute)
	text := newSnapshotter(h, h.started).render(*now)
	if strings.Contains(text, "kv00") {
		t.Fatalf("kvstore rows of a finished port:\n%s", text)
	}
	// Even after hours on a large host, the header line stays within headWidth.
	var many []int
	for i := 0; i < 120; i++ {
		many = append(many, 30000+i)
	}
	wide, wideNow := clockedHost(many...)
	for i := 0; i < 100; i++ {
		wide.port(30000 + i).finish(nil)
	}
	*wideNow = wideNow.Add(2*time.Hour + 5*time.Minute)
	assertNodeLogWidths(t, []logEntry{{levelProgress, newSnapshotter(wide, wide.started).render(*wideNow)}})
}

func TestKvProgressOfSortsKvstoresAndCountsTheirBinlogs(t *testing.T) {
	dir := t.TempDir()
	write := func(name string, size int) string {
		path := filepath.Join(dir, name)
		if err := os.WriteFile(path, make([]byte, size), 0644); err != nil {
			t.Fatal(err)
		}
		return path
	}
	kvs := kvProgressOf(map[int][]string{
		2: {write("a", 10), write("b", 20)},
		0: {write("c", 5)},
	})
	want := []kvProgress{
		{kvstore: 0, state: kvWaiting, total: 5, filesTotal: 1},
		{kvstore: 2, state: kvWaiting, total: 30, filesTotal: 2},
	}
	if fmt.Sprint(kvs) != fmt.Sprint(want) {
		t.Fatalf("got %+v, want %+v", kvs, want)
	}
}

func TestSnapshotMarksAStalledPortAndWarnsOnce(t *testing.T) {
	h, now := clockedHost(30000)
	p := h.port(30000)
	p.enter(phaseUnpack, 100, unitBytes)
	p.progressed(10)
	s := newSnapshotter(h, *now)
	var warnings []string
	var last string
	step := func(d time.Duration) {
		for end := now.Add(d); now.Before(end); {
			*now = now.Add(10 * time.Second)
			text, w := s.step(*now)
			warnings = append(warnings, w...)
			if text != "" {
				last = text
			}
		}
	}
	step(5 * time.Minute)
	if len(warnings) != 1 || warnings[0] != "[30000] stalled: unpack made no progress in 2m00s" {
		t.Fatalf("warnings %q", warnings)
	}
	if !strings.Contains(last, "stalled") {
		t.Fatalf("snapshot:\n%s", last)
	}
	p.progressed(10)
	step(time.Minute)
	if strings.Contains(last, "stalled") {
		t.Fatalf("still stalled:\n%s", last)
	}
	step(2 * time.Minute)
	if len(warnings) != 2 {
		t.Fatalf("warnings %q", warnings)
	}
}

// plusLines replays one kvstore of n binlogs and returns the node log and the detail file.
