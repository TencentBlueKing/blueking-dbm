package rollback

import (
	"compress/gzip"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

func TestMain(m *testing.M) {
	mylog.UnitTestInitLog()
	os.Exit(m.Run())
}

// Persistence mode is determined per port because master backups or Redis 7.x
// still produce raw RDB even when cluster mode is AOF.
func TestRenderAppendonlyPerPort(t *testing.T) {
	conf := "port 30000\nappendonly no\ndir /data/redis/30000/data\n"

	aof := renderAppendonly(conf, true)
	rdb := renderAppendonly(conf, false)

	if !strings.Contains(aof, "appendonly yes") {
		t.Fatalf("aof backup should turn appendonly on, got:\n%s", aof)
	}
	if !strings.Contains(rdb, "appendonly no") {
		t.Fatalf("rdb backup should keep appendonly off, got:\n%s", rdb)
	}
	if strings.Contains(aof, "appendonly no") {
		t.Fatalf("stale appendonly line left behind:\n%s", aof)
	}
}

// Append appendonly directive when missing rather than failing silently.
func TestRenderAppendonlyAppendsWhenAbsent(t *testing.T) {
	out := renderAppendonly("port 30000\ndir /data/redis/30000/data\n", true)

	if !strings.Contains(out, "appendonly yes") {
		t.Fatalf("expected appendonly to be appended, got:\n%s", out)
	}
}

// Commented directives and appendfilename must not be modified or mistaken for appendonly.
func TestRenderAppendonlyLeavesCommentedAndLookalikeLines(t *testing.T) {
	conf := "# appendonly yes\nappendfilename \"appendonly.aof\"\nappendonly no\n"

	out := renderAppendonly(conf, true)

	if !strings.Contains(out, "# appendonly yes") {
		t.Fatalf("commented line was rewritten:\n%s", out)
	}
	if !strings.Contains(out, "appendfilename \"appendonly.aof\"") {
		t.Fatalf("appendfilename was rewritten:\n%s", out)
	}
	if strings.Count(out, "\nappendonly yes") != 1 {
		t.Fatalf("expected exactly one effective appendonly line:\n%s", out)
	}
}

func TestFingerprintIgnoresOrderAndDirectory(t *testing.T) {
	left := Fingerprint([]string{"/a/full.split.001", "/a/full.split.000"})
	right := Fingerprint([]string{"/b/full.split.000", "/b/full.split.001"})

	if left != right {
		t.Fatalf("fingerprint should not depend on order or directory: %q vs %q", left, right)
	}
	if Fingerprint([]string{"one.rdb"}) == Fingerprint([]string{"other.rdb"}) {
		t.Fatal("different backups must not share a fingerprint")
	}
}

// Completed ports must be skipped on retry to avoid failing on in-use ports.
func TestDoneMarkerRoundTrip(t *testing.T) {
	instDir := t.TempDir()
	print := Fingerprint([]string{"full.rdb"})

	if IsDone(instDir, print) {
		t.Fatal("a fresh instance dir must not look done")
	}
	if err := MarkDone(instDir, print); err != nil {
		t.Fatalf("MarkDone: %v", err)
	}
	if !IsDone(instDir, print) {
		t.Fatal("expected the port to be recognised as done")
	}

	ClearDone(instDir)
	if IsDone(instDir, print) {
		t.Fatal("ClearDone should force a redo")
	}
}

// Different backup files must not match a previous done marker.
func TestDoneMarkerRejectsADifferentBackup(t *testing.T) {
	instDir := t.TempDir()
	if err := MarkDone(instDir, Fingerprint([]string{"old.rdb"})); err != nil {
		t.Fatalf("MarkDone: %v", err)
	}

	if IsDone(instDir, Fingerprint([]string{"new.rdb"})) {
		t.Fatal("a different backup round must not reuse the previous done marker")
	}
}

type fakeProber struct {
	replies []map[string]string
	calls   int
}

func (f *fakeProber) Info(string) (map[string]string, error) {
	i := f.calls
	if i >= len(f.replies) {
		i = len(f.replies) - 1
	}
	f.calls++
	return f.replies[i], nil
}

func TestWaitLoadedReturnsOnceLoadingFinishes(t *testing.T) {
	p := &fakeProber{replies: []map[string]string{
		{"loading": "1", "loading_loaded_perc": "10.00", "loading_eta_seconds": "45"},
		{"loading": "1", "loading_loaded_perc": "80.00", "loading_eta_seconds": "9"},
		{"loading": "0"},
	}}
	var percs []float64
	var etas []time.Duration
	onLoading := func(perc float64, eta time.Duration) {
		percs = append(percs, perc)
		etas = append(etas, eta)
	}

	if err := waitLoaded(p, onLoading, "2.2.2.2:30000", time.Second, time.Millisecond); err != nil {
		t.Fatalf("waitLoaded: %v", err)
	}
	if p.calls != 3 || len(percs) != 2 || percs[0] != 10 || percs[1] != 80 ||
		etas[0] != 45*time.Second || etas[1] != 9*time.Second {
		t.Fatalf("calls=%d percs=%v etas=%v", p.calls, percs, etas)
	}
}

func TestCacheWaitLoadedFeedsProgressSnapshot(t *testing.T) {
	root := passwordRoot(t)
	writeConf(t, root, 30000, "redis.conf", "requirepass s3cret\n")
	inst := InstanceRestore{DestPort: 30000}
	r := &cacheRestorer{Job: Job{DestIP: "2.2.2.2", Instances: []InstanceRestore{inst}, Host: dirHost{root: root}}}
	h, now := clockedHost(30000)
	port := h.port(30000)
	port.enter(phaseLoad, 0, "")
	s := newSnapshotter(h, *now)
	var snap string
	orig := waitLoadedFn
	waitLoadedFn = func(addr, password string, deadline time.Duration,
		onLoading func(perc float64, eta time.Duration)) (int64, int64, error) {
		if addr != "2.2.2.2:30000" || password != "s3cret" {
			t.Fatalf("addr=%q password=%q", addr, password)
		}
		onLoading(62.5, 40*time.Second)
		// A repeat at the same percentage only refreshes the engine's ETA, not changed.
		changed := port.prog.changed
		*now = now.Add(time.Minute)
		onLoading(62.5, 35*time.Second)
		if !port.prog.changed.Equal(changed) {
			t.Fatalf("changed moved without progress: %v -> %v", changed, port.prog.changed)
		}
		snap, _ = s.step(*now)
		return 1234, 64 << 20, nil
	}
	t.Cleanup(func() { waitLoadedFn = orig })

	window := newMemWindow(1<<30, 1)
	if err := window.acquire(100 << 20); err != nil {
		t.Fatal(err)
	}
	if err := r.waitLoaded(inst, newPortLog(30000), port, window, 100<<20); err != nil {
		t.Fatalf("waitLoaded: %v", err)
	}
	assertNodeLogWidths(t, []logEntry{{levelProgress, snap}})
	containsAll(t, snap, "30000  load     ██████░░░░  62%                             35s")
}

func TestWaitLoadedTimesOutWhileStillLoading(t *testing.T) {
	p := &fakeProber{replies: []map[string]string{{"loading": "1", "loading_loaded_perc": "42.00"}}}

	err := waitLoaded(p, nil, "2.2.2.2:30000", 20*time.Millisecond, time.Millisecond)
	if err == nil || !strings.Contains(err.Error(), "42.00") {
		t.Fatalf("expected a timeout reporting progress, got %v", err)
	}
}

func TestLoadDeadlineScalesWithSizeAndFormat(t *testing.T) {
	if LoadDeadline(0, false) != 5*time.Minute {
		t.Fatalf("empty data should get the minimum deadline, got %v", LoadDeadline(0, false))
	}
	if LoadDeadline(30<<30, false) != 35*time.Minute {
		t.Fatalf("30GB should get 35m, got %v", LoadDeadline(30<<30, false))
	}
	if LoadDeadline(1<<40, false) != 2*time.Hour {
		t.Fatalf("huge data should be capped at 2h, got %v", LoadDeadline(1<<40, false))
	}
	// AOF replays commands, about ten times slower per GB
	if LoadDeadline(30<<30, true) != 5*time.Minute+300*time.Minute {
		t.Fatalf("30GB AOF should get 5h5m, got %v", LoadDeadline(30<<30, true))
	}
	if LoadDeadline(1<<40, true) != 12*time.Hour {
		t.Fatalf("huge AOF should be capped at 12h, got %v", LoadDeadline(1<<40, true))
	}
}

// A retry must resume a port that is still loading this backup rather than kill it.
func TestPendingMarker(t *testing.T) {
	instDir := t.TempDir()
	print := Fingerprint([]string{"full.rdb"})

	if err := MarkPending(instDir, print); err != nil {
		t.Fatalf("MarkPending: %v", err)
	}
	if !IsPending(instDir, print) || IsPending(instDir, Fingerprint([]string{"other.rdb"})) {
		t.Fatal("pending marker should match only the same backup")
	}
	if IsDone(instDir, print) {
		t.Fatal("pending must not count as done")
	}
	if err := MarkDone(instDir, print); err != nil {
		t.Fatalf("MarkDone: %v", err)
	}
	if IsPending(instDir, print) {
		t.Fatal("MarkDone should clear the pending marker")
	}

	_ = MarkPending(instDir, print)
	ClearDone(instDir)
	if IsPending(instDir, print) || IsDone(instDir, print) {
		t.Fatal("ClearDone should clear both markers")
	}
}

func TestDataFileBytesPicksPlacedFile(t *testing.T) {
	dir := t.TempDir()
	if DataFileBytes(dir) != 0 {
		t.Fatal("empty data dir should report 0")
	}
	if err := os.WriteFile(filepath.Join(dir, "dump.rdb"), make([]byte, 128), 0644); err != nil {
		t.Fatal(err)
	}
	if DataFileBytes(dir) != 128 {
		t.Fatalf("expected 128, got %d", DataFileBytes(dir))
	}
}

func TestRunBoundedLimitsConcurrencyAndReturnsError(t *testing.T) {
	var inFlight, peak int32
	err := RunBounded(8, 2, func(i int) error {
		n := atomic.AddInt32(&inFlight, 1)
		for {
			p := atomic.LoadInt32(&peak)
			if n <= p || atomic.CompareAndSwapInt32(&peak, p, n) {
				break
			}
		}
		time.Sleep(2 * time.Millisecond)
		atomic.AddInt32(&inFlight, -1)
		if i == 3 {
			return errors.New("boom")
		}
		return nil
	})
	if err == nil || err.Error() != "boom" {
		t.Fatalf("expected boom, got %v", err)
	}
	if peak > 2 {
		t.Fatalf("expected at most 2 in flight, got %d", peak)
	}
}

func writeGzip(t *testing.T, path string, content []byte) {
	t.Helper()
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	w := gzip.NewWriter(f)
	if _, err = w.Write(content); err != nil {
		t.Fatal(err)
	}
	if err = w.Close(); err != nil {
		t.Fatal(err)
	}
}

// Decompressing must not copy the download into the work dir, and must leave it for retries.
func TestStageDecompressesFromSourceWithoutCopy(t *testing.T) {
	saveDir := t.TempDir()
	src := filepath.Join(saveDir, "1.1.1.9-30000-full.rdb.gz")
	writeGzip(t, src, []byte("REDIS0009"))

	staged, err := StageBackup(saveDir, filepath.Join(t.TempDir(), "30000"), InstanceRestore{SourceIP: "1.1.1.9",
		SourcePort: 30000, DestPort: 30000, FullFiles: []string{filepath.Base(src)}})
	if err != nil {
		t.Fatalf("StageBackup: %v", err)
	}
	if staged.IsAOF || filepath.Base(staged.DataFile) != "1.1.1.9-30000-full.rdb" {
		t.Fatalf("unexpected staged file %+v", staged)
	}
	entries, _ := os.ReadDir(staged.WorkDir)
	for _, e := range entries {
		if isCompressed(e.Name()) {
			t.Fatalf("compressed copy left in work dir: %s", e.Name())
		}
	}
	if _, err = os.Stat(src); err != nil {
		t.Fatalf("download must stay in place: %v", err)
	}
}

func TestStageLinksUncompressedBackup(t *testing.T) {
	saveDir := t.TempDir()
	src := filepath.Join(saveDir, "1.1.1.9-30000-full.rdb")
	if err := os.WriteFile(src, []byte("REDIS0009"), 0644); err != nil {
		t.Fatal(err)
	}

	staged, err := StageBackup(saveDir, filepath.Join(t.TempDir(), "30000"),
		InstanceRestore{DestPort: 30000, FullFiles: []string{filepath.Base(src)}})
	if err != nil {
		t.Fatalf("StageBackup: %v", err)
	}
	dataDir := t.TempDir()
	if err = os.Rename(staged.DataFile, filepath.Join(dataDir, "dump.rdb")); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(src); err != nil {
		t.Fatalf("moving the staged file must keep the download: %v", err)
	}
}

func TestParallelStagingKeepsPortsApart(t *testing.T) {
	saveDir := t.TempDir()
	insts := make([]InstanceRestore, 4)
	for i := range insts {
		name := fmt.Sprintf("1.1.1.9-%d-full.rdb.gz", 30000+i)
		writeGzip(t, filepath.Join(saveDir, name), []byte(fmt.Sprintf("port-%d", i)))
		insts[i] = InstanceRestore{DestPort: 30000 + i, FullFiles: []string{name}}
	}

	unpackDir := t.TempDir()
	staged := make([]StagedBackup, len(insts))
	if err := RunBounded(len(insts), 2, func(i int) error {
		var err error
		staged[i], err = StageBackup(saveDir, filepath.Join(unpackDir, fmt.Sprint(insts[i].DestPort)), insts[i])
		return err
	}); err != nil {
		t.Fatalf("parallel staging: %v", err)
	}
	for i, item := range staged {
		data, err := os.ReadFile(item.DataFile)
		if err != nil || string(data) != fmt.Sprintf("port-%d", i) {
			t.Fatalf("port %d got %q (%v)", 30000+i, data, err)
		}
	}
}

func TestCleanupStagedOnlyTouchesItsOwnPort(t *testing.T) {
	saveDir, unpackDir := t.TempDir(), t.TempDir()
	done := InstanceRestore{DestPort: 30000, FullFiles: []string{"1.1.1.9-30000-full.rdb.gz"}}
	other := InstanceRestore{DestPort: 30001, FullFiles: []string{"1.1.1.9-30001-full.rdb.gz"}}
	workDir := func(inst InstanceRestore) string { return filepath.Join(unpackDir, fmt.Sprint(inst.DestPort)) }
	for _, inst := range []InstanceRestore{done, other} {
		writeGzip(t, filepath.Join(saveDir, inst.FullFiles[0]), []byte("REDIS0009"))
		if _, err := StageBackup(saveDir, workDir(inst), inst); err != nil {
			t.Fatalf("StageBackup: %v", err)
		}
	}

	if err := CleanupStaged(saveDir, workDir(done), done); err != nil {
		t.Fatalf("CleanupStaged: %v", err)
	}
	for _, p := range []string{filepath.Join(saveDir, done.FullFiles[0]), workDir(done)} {
		if _, err := os.Stat(p); !os.IsNotExist(err) {
			t.Fatalf("%s should be removed", p)
		}
	}
	for _, p := range []string{filepath.Join(saveDir, other.FullFiles[0]), workDir(other)} {
		if _, err := os.Stat(p); err != nil {
			t.Fatalf("%s should be kept: %v", p, err)
		}
	}
	if err := CleanupStaged(saveDir, workDir(InstanceRestore{DestPort: 30002}), InstanceRestore{DestPort: 30002}); err != nil {
		t.Fatalf("placeholder cleanup should be a no-op: %v", err)
	}
}

func TestDefaultSaveDirEndsWithRecoverSubDir(t *testing.T) {
	if filepath.Base(DefaultSaveDir()) != "recover_redis" {
		t.Fatalf("unexpected save dir: %s", DefaultSaveDir())
	}
}
