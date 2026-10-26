package rollback

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// --- 9.1 host limits ------------------------------------------------------------------

func TestLimitsFollowTheHostAndOnlyGoDown(t *testing.T) {
	auto := Limits{CPU: 16}
	auto.Unpack = auto.capped(auto.CPU / 2)
	if auto.Unpack != 8 || auto.Replay(4) != 4 || auto.Replay(20) != 16 || auto.Parse() != 11 ||
		auto.Loading() != 16 || auto.KvstoreReplay(4) != 4 || auto.KvstoreReplay(70) != 8 {
		t.Fatalf("auto limits: unpack=%d replay=%d/%d parse=%d loading=%d kvstore replay=%d/%d",
			auto.Unpack, auto.Replay(4), auto.Replay(20), auto.Parse(), auto.Loading(),
			auto.KvstoreReplay(4), auto.KvstoreReplay(70))
	}
	// 10-21: 32 cores, 24 ports all replay instead of 16, parsing on 22 cores
	if prod := (Limits{CPU: 32}); prod.Replay(24) != 24 || prod.Parse() != 22 {
		t.Fatalf("32 cores: replay=%d parse=%d", prod.Replay(24), prod.Parse())
	}
	low := Limits{CPU: 16, Max: 2}
	if low.capped(8) != 2 || low.Replay(4) != 2 || low.Parse() != 2 || low.KvstoreReplay(70) != 2 {
		t.Fatal("max_concurrency should lower every stage")
	}
	high := Limits{CPU: 4, Max: 64}
	if high.capped(high.CPU/2) != 2 || high.Replay(20) != 4 || high.Parse() != 2 {
		t.Fatal("max_concurrency must not raise a stage above the host")
	}
	if (Limits{CPU: 1}).Parse() != 1 || (Limits{CPU: 1}).KvstoreReplay(3) != 1 {
		t.Fatal("every stage keeps at least one slot")
	}
}

func TestParseMemAvailable(t *testing.T) {
	got, err := parseMemAvailable(strings.NewReader("MemTotal: 65536 kB\nMemFree: 1 kB\nMemAvailable: 1024 kB\n"))
	if err != nil || got != 1024*1024 {
		t.Fatalf("got %d err=%v", got, err)
	}
	if _, err = parseMemAvailable(strings.NewReader("MemTotal: 1 kB\n")); err == nil {
		t.Fatal("want error without MemAvailable")
	}
}

// --- 9.4 / 9.12 memory window ---------------------------------------------------------

func TestMemWindowNeverExceedsBudgetAndRefillsOnLoad(t *testing.T) {
	// budget is 90% of 100
	w := newMemWindow(100, 16)
	var used, peak int64
	var mu sync.Mutex
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := w.acquire(40); err != nil {
				t.Error(err)
				return
			}
			mu.Lock()
			used += 40
			if used > peak {
				peak = used
			}
			mu.Unlock()
			time.Sleep(time.Millisecond)
			mu.Lock()
			used -= 40
			mu.Unlock()
			// its real RSS is far below the estimate, which frees room for the next port
			w.loaded(40, 1)
		}()
	}
	wg.Wait()
	if peak > 80 {
		t.Fatalf("window let %d in, budget 90", peak)
	}
}

func TestMemWindowFailsWhenNothingCanFreeMemory(t *testing.T) {
	w := newMemWindow(100, 16)
	if err := w.acquire(60); err != nil {
		t.Fatal(err)
	}
	w.loaded(60, 0)
	if err := w.acquire(60); err == nil || !strings.Contains(err.Error(), "not enough memory") {
		t.Fatalf("loaded instances keep their memory, want failure, got %v", err)
	}
	if err := w.reserve(31); err == nil {
		t.Fatal("reserve past the budget must fail")
	}
	if err := w.reserve(30); err != nil {
		t.Fatal(err)
	}
	w.unreserve(30)
	if err := w.reserve(30); err != nil || w.loading != 0 {
		t.Fatalf("unreserve must give back only the memory: err=%v loading=%d", err, w.loading)
	}
}

func TestMemWindowBoundsLoadingByCPU(t *testing.T) {
	w := newMemWindow(0, 1)
	if err := w.acquire(1); err != nil {
		t.Fatal(err)
	}
	second := make(chan error)
	go func() { second <- w.acquire(1) }()
	select {
	case <-second:
		t.Fatal("second load must wait for a loading slot")
	case <-time.After(20 * time.Millisecond):
	}
	w.loaded(1, 0)
	if err := <-second; err != nil {
		t.Fatal(err)
	}
}

func TestSSDMemoryReadsCachesFromConf(t *testing.T) {
	conf := filepath.Join(t.TempDir(), "redis.conf")
	content := "port 30000\nrocksdb_block_cache 500000000\nrocksdb_write_buffer_size 32000000\n# rocksdb_block_cache 1\n"
	if err := os.WriteFile(conf, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	if got := SSDMemory(conf); got != 564000000 {
		t.Fatalf("got %d", got)
	}
	if SSDMemory(filepath.Join(t.TempDir(), "none")) != 0 {
		t.Fatal("missing conf takes nothing")
	}
}

func TestSetPersistenceTurnsSaveOffAndFollowsFormat(t *testing.T) {
	conf := filepath.Join(t.TempDir(), "redis.conf")
	if err := os.WriteFile(conf, []byte("save 900 1\nsave 300 10\nappendonly yes\n"), 0644); err != nil {
		t.Fatal(err)
	}
	// chown to mysql fails off the target hosts; the content is written before it
	_ = SetPersistence(conf, false)
	raw, _ := os.ReadFile(conf)
	if got := string(raw); got != "save \"\"\nappendonly no\n" {
		t.Fatalf("got %q", got)
	}
}

// --- 9.10 parse ahead, apply in order -------------------------------------------------

func TestPipelineAppliesInOrderWhateverParseOrder(t *testing.T) {
	const n = 30
	pool := make(chan struct{}, 8)
	var applied []int
	var outstanding, peak int32
	err := runPipeline(n, parseLookahead, pool, func(i int) error {
		v := atomic.AddInt32(&outstanding, 1)
		for p := atomic.LoadInt32(&peak); v > p && !atomic.CompareAndSwapInt32(&peak, p, v); p = atomic.LoadInt32(&peak) {
		}
		time.Sleep(time.Duration(rand.Intn(3)) * time.Millisecond)
		return nil
	}, func(i int) error {
		applied = append(applied, i)
		atomic.AddInt32(&outstanding, -1)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	for i, v := range applied {
		if v != i {
			t.Fatalf("applied out of order: %v", applied)
		}
	}
	if len(applied) != n {
		t.Fatalf("applied %d of %d", len(applied), n)
	}
	if peak > parseLookahead {
		t.Fatalf("%d parsed ahead, limit %d", peak, parseLookahead)
	}
}

func TestPipelineStopsApplyingAfterAFailure(t *testing.T) {
	pool := make(chan struct{}, 4)
	for _, failAt := range []string{"parse", "apply"} {
		var applied []int
		boom := errors.New("boom")
		err := runPipeline(10, parseLookahead, pool, func(i int) error {
			if failAt == "parse" && i == 3 {
				return boom
			}
			return nil
		}, func(i int) error {
			if failAt == "apply" && i == 3 {
				return boom
			}
			applied = append(applied, i)
			return nil
		})
		if !errors.Is(err, boom) || fmt.Sprint(applied) != "[0 1 2]" {
			t.Fatalf("%s failure: applied %v err=%v", failAt, applied, err)
		}
	}
	if len(pool) != 0 {
		t.Fatal("parse slots leaked")
	}
}

func TestPortsWithMoreBinlogsGoFirst(t *testing.T) {
	insts := []InstanceRestore{{DestPort: 30000}, {DestPort: 30001}, {DestPort: 30002}}
	sortLongestFirst(insts, map[int]portPlan{30000: {binlogBytes: 1}, 30001: {binlogBytes: 9}, 30002: {binlogBytes: 5}})
	if fmt.Sprint(portsOf(insts)) != "[30001 30002 30000]" {
		t.Fatalf("got %v", portsOf(insts))
	}
}

// --- 9.5 / 9.7 logs and summaries -----------------------------------------------------

func TestPortLogNamesPortShardAndSource(t *testing.T) {
	inst := InstanceRestore{ShardValue: "0-104999", SourceIP: "1.1.1.1", SourcePort: 30000, DestPort: 30001}
	if got := newPortLog("2.2.2.2", inst).prefix; got != "[dest=2.2.2.2:30001 shard=0-104999 src=1.1.1.1:30000] " {
		t.Fatalf("got %q", got)
	}
}

func TestResultListsFailedPortsAndReplayErrors(t *testing.T) {
	h := newHostReport("2.2.2.2", "tendisssd", []InstanceRestore{{DestPort: 30001}, {DestPort: 30000}, {DestPort: 30002}})
	ok := h.port(30000)
	ok.add(stageUnpack, 2*time.Second)
	ok.replayed(3, replyStats{Lines: 10, Errors: 4, Expected: 1})
	ok.finish(nil)
	h.port(30001).finish(errors.New("apply binlog x failed"))
	text := h.resultText()
	for _, want := range []string{
		"done=1 skipped=0 failed=1 not run=1",
		"port 30000 shard= src=:0 done unpack=2s binlogs=3",
		"failed ports: [30001]",
		"port(errors): [30000(3)]",
		"error: apply binlog x failed",
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("summary misses %q:\n%s", want, text)
		}
	}
}

func TestResultShowsChildCPUNextToWallTime(t *testing.T) {
	h := newHostReport("2.2.2.2", "tendisssd", []InstanceRestore{{DestPort: 30000}})
	p := h.port(30000)
	p.add(stageParse, 17*time.Minute)
	p.addCPU(stageParse, 9*time.Minute)
	p.add(stageApply, 3*time.Minute)
	p.finish(nil)
	text := h.resultText()
	if !strings.Contains(text, "parse=17m0s(cpu 9m0s) apply=3m0s") || strings.Contains(text, "download") {
		t.Fatalf("got:\n%s", text)
	}
}

func TestUnpackReportsCPUTime(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "dump.rdb.gz")
	if _, err := runStageCmd(fmt.Sprintf("head -c 4000000 /dev/urandom | gzip > %s", src)); err != nil {
		t.Fatal(err)
	}
	cpu, err := unpackBackup([]string{src}, filepath.Join(dir, "work"))
	if err != nil || cpu <= 0 {
		t.Fatalf("cpu=%v err=%v", cpu, err)
	}
}

// --- 9.15 / 9.17 unpack onto the data disk --------------------------------------------

func TestPlaceFileRenamesOnOneFilesystem(t *testing.T) {
	dir := t.TempDir()
	src, dst := filepath.Join(dir, "a"), filepath.Join(dir, "b")
	if err := os.WriteFile(src, []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}
	st, _ := os.Stat(src)
	if err := placeFile(portLog{}, src, dst); err != nil {
		t.Fatal(err)
	}
	moved, err := os.Stat(dst)
	if err != nil || !os.SameFile(st, moved) {
		t.Fatalf("want the same inode moved, err=%v", err)
	}
}

func TestPlaceFileCopiesAcrossFilesystems(t *testing.T) {
	sameDeviceFn = func(a, b string) (bool, error) { return false, nil }
	defer func() { sameDeviceFn = sameDevice }()
	dir := t.TempDir()
	src, dst := filepath.Join(dir, "a"), filepath.Join(dir, "b")
	if err := os.WriteFile(src, []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}
	st, _ := os.Stat(src)
	if err := placeFile(portLog{}, src, dst); err != nil {
		t.Fatal(err)
	}
	copied, err := os.Stat(dst)
	if err != nil || os.SameFile(st, copied) {
		t.Fatalf("want a copy, err=%v", err)
	}
	if _, err = os.Stat(src); !os.IsNotExist(err) {
		t.Fatal("the source is removed after copying")
	}
}

func TestJobUnpacksEachPortIntoItsOwnDir(t *testing.T) {
	j := Job{UnpackDir: "/data1/recover_redis"}
	if got := j.portWorkDir(30001); got != "/data1/recover_redis/30001" {
		t.Fatalf("got %s", got)
	}
}

// --- 10.5 exact names, broken backups named -------------------------------------------

func TestResolveFilesNeedsExactNames(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "x-1.1.1.1-30000-full.rdb.zst.bak")
	_, err := resolveFiles(dir, InstanceRestore{SourceIP: "1.1.1.1", SourcePort: 30000,
		FullFiles: []string{"1.1.1.1-30000-full.rdb.zst"}})
	if err == nil || !strings.Contains(err.Error(), "missing") {
		t.Fatalf("a lookalike file must not stand in, got %v", err)
	}
}

func TestBrokenBackupIsReportedAsCorrupted(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "1.1.1.1-30000-full.rdb.gz")
	_, err := StageBackup(dir, filepath.Join(t.TempDir(), "30000"),
		InstanceRestore{DestPort: 30000, FullFiles: []string{"1.1.1.1-30000-full.rdb.gz"}})
	if err == nil || !strings.Contains(err.Error(), "备份文件损坏") || !strings.Contains(err.Error(), "full.rdb.gz") {
		t.Fatalf("got %v", err)
	}
}

// --- 10.3 / 10.6 downloaded file verification -----------------------------------------

func writeManifest(t *testing.T, dir string, lines ...string) string {
	t.Helper()
	body := ""
	for _, l := range lines {
		body += l + "\n"
	}
	sum := sha256.Sum256([]byte(body))
	fp := hex.EncodeToString(sum[:])
	content := fmt.Sprintf("# redis rollback manifest plan=7 files=%d sha256=%s\n%s", len(lines), fp, body)
	if err := os.WriteFile(filepath.Join(dir, "rollback_manifest_7"), []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return fp
}

func TestVerifyPassesWhenEveryFileMatches(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "a.tar", "binlog-1.log.zst")
	fp := writeManifest(t, dir, "a.tar 1 -", "binlog-1.log.zst 1 -")
	if err := VerifyDownloads(dir, "rollback_manifest_7", fp); err != nil {
		t.Fatal(err)
	}
}

func TestVerifyListsMissingAndMismatchedFiles(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "a.tar", "b.tar", "a.tar.split.000")
	fp := writeManifest(t, dir, "a.tar 1 -", "b.tar 9 -", "c.tar 1 -")
	err := VerifyDownloads(dir, "rollback_manifest_7", fp)
	if err == nil {
		t.Fatal("want error")
	}
	for _, want := range []string{"1 of 3 files missing [c.tar]", "1 mismatched [b.tar(size want 9 got 1)]"} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("err=%v, want %q", err, want)
		}
	}
}

func TestVerifyChecksMD5WhenGiven(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "a.tar")
	// md5("x")
	fp := writeManifest(t, dir, "a.tar 1 9dd4e461268c8034f5c8564e155c67a6")
	if err := VerifyDownloads(dir, "rollback_manifest_7", fp); err != nil {
		t.Fatal(err)
	}
	fp = writeManifest(t, dir, "a.tar 1 00000000000000000000000000000000")
	if err := VerifyDownloads(dir, "rollback_manifest_7", fp); err == nil || !strings.Contains(err.Error(), "md5") {
		t.Fatalf("got %v", err)
	}
}

func TestVerifyRejectsDamagedOrForeignManifest(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, "a.tar", "b.tar")
	writeManifest(t, dir, "a.tar 1 -", "b.tar 1 -")
	if err := VerifyDownloads(dir, "rollback_manifest_7", strings.Repeat("0", 64)); err == nil {
		t.Fatal("want error for a manifest of another plan")
	}
	path := filepath.Join(dir, "rollback_manifest_7")
	raw, _ := os.ReadFile(path)
	// the push lost the last line
	if err := os.WriteFile(path, raw[:len(raw)-len("b.tar 1 -\n")], 0644); err != nil {
		t.Fatal(err)
	}
	if err := VerifyDownloads(dir, "rollback_manifest_7", ""); err == nil || !strings.Contains(err.Error(), "damaged") {
		t.Fatalf("want error for a truncated manifest, got %v", err)
	}
}

func TestManifestMatchesThePlannerFormat(t *testing.T) {
	// rollback_manifest() in plan.py renders exactly this for one 10-byte a.tar
	content := "# redis rollback manifest plan=7 files=1 sha256=" +
		"384a670cfdfb23a96aa85ef3d45008bcdf4cc36ff0ec809984d2d8595fe803a7\na.tar 10 -\n"
	entries, fp, err := ParseManifest([]byte(content))
	if err != nil || len(entries) != 1 || entries[0] != (ManifestEntry{Name: "a.tar", Size: 10, MD5: "-"}) {
		t.Fatalf("entries=%v err=%v", entries, err)
	}
	if fp != "384a670cfdfb23a96aa85ef3d45008bcdf4cc36ff0ec809984d2d8595fe803a7" {
		t.Fatalf("fingerprint %s differs from the planner's", fp)
	}
}
