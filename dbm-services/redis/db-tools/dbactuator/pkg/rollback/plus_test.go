package rollback

import (
	"compress/gzip"
	"encoding/base64"
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

// replLogKey builds a base64 ReplLogKeyV2: chunk id, type, db id, then the binlog id.
func replLogKey(id uint64) string {
	raw := []byte{0xff, 0xff, 0xff, 0x01, 'B', 0xff, 0xff, 0xff, 0x01}
	raw = binary.BigEndian.AppendUint64(raw, id)
	raw = append(raw, 0)
	return base64.StdEncoding.EncodeToString(raw)
}

func restoreLine(kvstore int, id uint64) string {
	return fmt.Sprintf("restorebinlogv2 %d %s dmFsdWU=", kvstore, replLogKey(id))
}

func TestBinlogIDFromKey(t *testing.T) {
	if id, err := binlogIDFromKey(replLogKey(123456789)); err != nil || id != 123456789 {
		t.Fatalf("id=%d err=%v", id, err)
	}
	for _, bad := range []string{"not base64!", base64.StdEncoding.EncodeToString([]byte("short")), replLogKey(0)} {
		if _, err := binlogIDFromKey(bad); err == nil {
			t.Fatalf("%q: want error", bad)
		}
	}
}

func TestParseRestoreLine(t *testing.T) {
	args, id, err := parseRestoreLine(restoreLine(3, 42), 3)
	if err != nil || id != 42 || len(args) != 4 || args[0] != restoreBinlogCmd {
		t.Fatalf("args=%v id=%d err=%v", args, id, err)
	}
	if args, _, err = parseRestoreLine("  ", 3); args != nil || err != nil {
		t.Fatalf("blank line: %v %v", args, err)
	}
	if _, _, err = parseRestoreLine(restoreLine(4, 42), 3); err == nil || !strings.Contains(err.Error(), "kvstore 4") {
		t.Fatalf("err=%v", err)
	}
}

// fakeReplayer applies restorebinlogv2 by moving binlogpos to the id it carries. Like tendisplus,
// a failed command does not stop the rest of its batch.
type fakeReplayer struct {
	pos     uint64
	applied []uint64
	batches int
	drop    uint64
	fail    uint64
}

func (f *fakeReplayer) BinlogPos(int) (uint64, error) { return f.pos, nil }

func (f *fakeReplayer) execBatch(cmds [][]string) ([]error, error) {
	f.batches++
	replies := make([]error, len(cmds))
	for i, args := range cmds {
		id, _ := binlogIDFromKey(args[2])
		if id == f.fail {
			replies[i] = fmt.Errorf("ERR apply failed")
			continue
		}
		f.applied = append(f.applied, id)
		if id != f.drop {
			f.pos = id
		}
	}
	return replies, nil
}

// gzipBinlogs writes binlog files the replay can decompress without zstd.
func gzipBinlogs(t *testing.T, dir string, names ...string) []string {
	t.Helper()
	var paths []string
	for _, name := range names {
		path := filepath.Join(dir, name+".gz")
		f, err := os.Create(path)
		if err != nil {
			t.Fatal(err)
		}
		w := gzip.NewWriter(f)
		_, _ = w.Write([]byte("binlog"))
		_ = w.Close()
		_ = f.Close()
		paths = append(paths, path)
	}
	return paths
}

// fakeBinlogTool emits the ids of each file at or after the start position, like binlog_tool.
func fakeBinlogTool(t *testing.T, ids map[string][]uint64, ignoreStart bool) func() {
	t.Helper()
	binlogToolFn = func(logFile string, startPos uint64, _ int64, onLine func(string) error) (time.Duration, error) {
		if _, err := os.Stat(logFile); err != nil {
			t.Fatalf("binlog not decompressed: %v", err)
		}
		for _, id := range ids[filepath.Base(logFile)] {
			if id < startPos && !ignoreStart {
				continue
			}
			if err := onLine(restoreLine(2, id)); err != nil {
				return time.Second, err
			}
		}
		return time.Second, nil
	}
	return func() { binlogToolFn = runBinlogTool }
}

func replayFixture(t *testing.T) ([]string, map[string][]uint64, *portReport) {
	files := gzipBinlogs(t, t.TempDir(), "binlog-a.log", "binlog-b.log")
	ids := map[string][]uint64{"binlog-a.log": {98, 99, 100, 101, 102}, "binlog-b.log": {103, 104, 105}}
	p := newHostReport("2.2.2.2", "tendisplus", []InstanceRestore{{DestPort: 30000}}).port(30000)
	return files, ids, p
}

func TestReplayKvstoreAppliesOnlyAfterBinlogpos(t *testing.T) {
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, false)()
	// 103 is a retry that already replayed into the second file.
	for pos, want := range map[uint64][]uint64{100: {101, 102, 103, 104, 105}, 103: {104, 105}} {
		cli := &fakeReplayer{pos: pos}
		n, err := replayKvstore(portLog{}, p, cli, 2, files, 0, t.TempDir(), nil)
		if err != nil || n != len(want) || !reflect.DeepEqual(cli.applied, want) {
			t.Fatalf("pos=%d: n=%d applied=%v err=%v", pos, n, cli.applied, err)
		}
	}
}

func TestReplayKvstoreFailsWhenBinlogposMissesAWrite(t *testing.T) {
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, false)()
	_, err := replayKvstore(portLog{}, p, &fakeReplayer{pos: 100, drop: 105}, 2, files, 0, t.TempDir(), nil)
	if !failedInFlight(err) || !strings.Contains(err.Error(), "kvstore 2 binlogpos is 104 after replay, want 105") {
		t.Fatalf("err=%v", err)
	}
}

func TestReplayKvstoreStopsOnTheFirstErrorReply(t *testing.T) {
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, false)()
	cli := &fakeReplayer{pos: 100, fail: 102}
	_, err := replayKvstore(portLog{}, p, cli, 2, files, 0, t.TempDir(), nil)
	if err == nil || !strings.Contains(err.Error(), "restorebinlogv2 of binlog id 102 failed") {
		t.Fatalf("err=%v", err)
	}
	if !reflect.DeepEqual(cli.applied, []uint64{101}) || cli.batches != 1 {
		t.Fatalf("applied %v in %d batches after the failure", cli.applied, cli.batches)
	}
	if !failedInFlight(err) {
		t.Fatalf("a failed batch must not be resumed from binlogpos: %v", err)
	}
}

func TestReplayKvstoreBatchFailureLeavesBinlogposPastTheHole(t *testing.T) {
	// Why a failed batch forces a redo: the writes after 99 went in, so binlogpos is past it.
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, false)()
	cli := &fakeReplayer{pos: 98, fail: 99}
	_, err := replayKvstore(portLog{}, p, cli, 2, files, 0, t.TempDir(), nil)
	if !failedInFlight(err) || cli.pos != 102 || !reflect.DeepEqual(cli.applied, []uint64{100, 101, 102}) {
		t.Fatalf("err=%v pos=%d applied=%v", err, cli.pos, cli.applied)
	}
}

func TestReplayKvstoreToolFailureBetweenBatchesCanResume(t *testing.T) {
	files, _, p := replayFixture(t)
	binlogToolFn = func(_ string, _ uint64, _ int64, onLine func(string) error) (time.Duration, error) {
		if err := onLine(restoreLine(2, 101)); err != nil {
			return 0, err
		}
		return 0, fmt.Errorf("binlog_tool failed")
	}
	defer func() { binlogToolFn = runBinlogTool }()
	cli := &fakeReplayer{pos: 100}
	_, err := replayKvstore(portLog{}, p, cli, 2, files, 0, t.TempDir(), nil)
	if err == nil || failedInFlight(err) || cli.batches != 0 {
		t.Fatalf("err=%v batches=%d: the unsent part is dropped and binlogpos stays exact", err, cli.batches)
	}
}

func TestReplayKvstoreRecordsToolCPU(t *testing.T) {
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, false)()
	if _, err := replayKvstore(portLog{}, p, &fakeReplayer{pos: 100}, 2, files, 0, t.TempDir(), nil); err != nil {
		t.Fatal(err)
	}
	if p.cpu[stageApply] != 2*time.Second {
		t.Fatalf("apply cpu=%v, want binlog_tool's 1s per file", p.cpu[stageApply])
	}
}

func TestReplayKvstoreRejectsIdsAtOrBelowTheStart(t *testing.T) {
	// Ids not after binlogpos mean they are misread or binlog_tool ignored the start position:
	// skipping them could hide lost writes, so nothing is applied.
	files, ids, p := replayFixture(t)
	defer fakeBinlogTool(t, ids, true)()
	cli := &fakeReplayer{pos: 100}
	_, err := replayKvstore(portLog{}, p, cli, 2, files, 0, t.TempDir(), nil)
	if !failedInFlight(err) || !strings.Contains(err.Error(), "binlog id 98 is not after 100") ||
		len(cli.applied) != 0 {
		t.Fatalf("err=%v applied=%v", err, cli.applied)
	}
}

func TestReplayKvstoreFailsOnUndecodableBinlog(t *testing.T) {
	files, _, p := replayFixture(t)
	binlogToolFn = func(_ string, _ uint64, _ int64, onLine func(string) error) (time.Duration, error) {
		return 0, onLine("ERR: invalid binlog, skip the rest")
	}
	defer func() { binlogToolFn = runBinlogTool }()
	_, err := replayKvstore(portLog{}, p, &fakeReplayer{pos: 100}, 2, files, 0, t.TempDir(), nil)
	if err == nil || !strings.Contains(err.Error(), "binlog-a.log.gz") ||
		!strings.Contains(err.Error(), "cannot decode a binlog") {
		t.Fatalf("err=%v", err)
	}
}

func plusInstance(chains map[int][]string) InstanceRestore {
	inst := InstanceRestore{SourceIP: "1.1.1.1", SourcePort: 30000, DestPort: 30000}
	for kvstore := 0; kvstore < len(chains); kvstore++ {
		inst.KvstoreBinlogs = append(inst.KvstoreBinlogs, KvstoreBinlogs{
			Kvstore:           kvstore,
			BinlogRange:       BinlogRange{FirstIndex: 10, LastIndex: 11},
			BinlogCount:       len(chains[kvstore]),
			BinlogFingerprint: BinlogFingerprint(chains[kvstore]),
		})
	}
	return inst
}

var plusChains = map[int][]string{
	0: {"binlog-1.1.1.1-30000-0-0000010-20260101000000.log.zst", "binlog-1.1.1.1-30000-0-0000011-20260101010000.log.zst"},
	1: {"binlog-1.1.1.1-30000-1-0000010-20260101000000.log.zst", "binlog-1.1.1.1-30000-1-0000011-20260101010000.log.zst"},
}

func TestLocalKvstoreBinlogsChecksEveryKvstore(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, plusChains[0]...)
	touch(t, dir, plusChains[1]...)
	// another instance, an SSD name and an out-of-range index share the dir
	touch(t, dir, "binlog-1.1.1.1-30001-0-0000010-20260101000000.log.zst",
		"binlog-1.1.1.1-30000-0000010-20260101000000.log.zst",
		"binlog-1.1.1.1-30000-1-0000012-20260101020000.log.zst")
	chains, err := LocalKvstoreBinlogs(dir, plusInstance(plusChains))
	if err != nil {
		t.Fatal(err)
	}
	for kvstore, names := range plusChains {
		var got []string
		for _, f := range chains[kvstore] {
			got = append(got, filepath.Base(f))
		}
		if !reflect.DeepEqual(got, names) {
			t.Fatalf("kvstore %d: %v", kvstore, got)
		}
	}

	dir = t.TempDir()
	touch(t, dir, plusChains[0]...)
	touch(t, dir, plusChains[1][0])
	_, err = LocalKvstoreBinlogs(dir, plusInstance(plusChains))
	if err == nil || !strings.Contains(err.Error(), "1.1.1.1:30000 kvstore 1") ||
		!strings.Contains(err.Error(), "missing [11]") {
		t.Fatalf("err=%v", err)
	}
}

func TestPlusFingerprintCoversEveryKvstore(t *testing.T) {
	inst := plusInstance(plusChains)
	inst.FullFiles = []string{"a.tar"}
	other := plusInstance(plusChains)
	other.FullFiles = []string{"a.tar"}
	other.KvstoreBinlogs[1].BinlogFingerprint = "x"
	if inst.Fingerprint() == other.Fingerprint() || !strings.HasPrefix(inst.Fingerprint(), "a.tar|0:") {
		t.Fatalf("%s vs %s", inst.Fingerprint(), other.Fingerprint())
	}
}

func writeBackup(t *testing.T, kvstores ...int) string {
	t.Helper()
	root := filepath.Join(t.TempDir(), "3-TENDISPLUS-FULL-slave-1.1.1.1-30000-20260101-010000")
	for _, kvstore := range kvstores {
		dir := filepath.Join(root, fmt.Sprint(kvstore))
		if err := os.MkdirAll(dir, 0755); err != nil {
			t.Fatal(err)
		}
		meta := fmt.Sprintf(`{"backupType":1,"binlogpos":%d,"startTimeSec":1,"binlogVersion":2}`, 100+kvstore)
		if err := os.WriteFile(filepath.Join(dir, "backup_meta"), []byte(meta), 0644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func TestPlusBackupRootAndMetas(t *testing.T) {
	root := writeBackup(t, 0, 1)
	got, err := plusBackupRoot(filepath.Dir(root))
	if err != nil || got != root {
		t.Fatalf("root=%s err=%v", got, err)
	}
	metas, err := readPlusBackupMetas(root)
	if err != nil || len(metas) != 2 || metas[1].BinlogPos != 101 || metas[0].BinlogVersion != 2 {
		t.Fatalf("metas=%v err=%v", metas, err)
	}
	if _, err = readPlusBackupMetas(writeBackup(t, 0, 2)); err == nil {
		t.Fatal("want error for kvstores not numbered 0..n-1")
	}
	if _, err = plusBackupRoot(t.TempDir()); err == nil {
		t.Fatal("want error without a backup")
	}
}

func TestCheckPlusBackupGates(t *testing.T) {
	metas := map[int]plusBackupMeta{0: {BinlogVersion: 2}, 1: {BinlogVersion: 2}}
	media := "tendisplus-2.8.2-rocksdb-v8.5.3"
	if err := checkPlusBackup(plusInstance(plusChains), metas, "2", media); err != nil {
		t.Fatal(err)
	}
	cases := map[string]struct {
		inst     InstanceRestore
		kvstores string
		media    string
		want     string
	}{
		"kvstore count":    {plusInstance(plusChains), "10", media, "backup holds 2 kvstores but the temp instance has 10"},
		"planned chains":   {plusInstance(map[int][]string{0: plusChains[0]}), "2", media, "1 binlog chains are planned"},
		"binlog version":   {InstanceRestore{}, "2", "tendisplus-1.9.0", "binlog version 2, newer than"},
		"bad kvstorecount": {InstanceRestore{}, "x", media, "invalid kvstorecount"},
	}
	for name, tc := range cases {
		err := checkPlusBackup(tc.inst, metas, tc.kvstores, tc.media)
		if err == nil || !strings.Contains(err.Error(), tc.want) {
			t.Fatalf("%s: err=%v", name, err)
		}
	}
	// a placeholder plans no chains; a media that does not tell its version is not judged
	if err := checkPlusBackup(InstanceRestore{}, metas, "2", "custom-build"); err != nil {
		t.Fatal(err)
	}
}

// dirHost keeps each port's instance dir under one root; nothing is started.
type dirHost struct{ root string }

func (h dirHost) InstallTools() error         { return nil }
func (h dirHost) Prepare([]int) error         { return nil }
func (h dirHost) InstanceDir(port int) string { return filepath.Join(h.root, fmt.Sprint(port)) }
func (h dirHost) Start(int) error             { return nil }
func (h dirHost) Stop(int) error              { return nil }
func (h dirHost) MediaName() string           { return "tendisplus-2.8.2-rocksdb-v8.5.3" }

func TestPlusClusterStepsFollowTheClusterFlag(t *testing.T) {
	var assigned []int
	assignPortSlotsFn = func(_ portLog, _ string, inst InstanceRestore) error {
		assigned = append(assigned, inst.DestPort)
		return nil
	}
	defer func() { assignPortSlotsFn = assignPortSlots }()

	for _, cluster := range []bool{false, true} {
		assigned = nil
		host := dirHost{root: t.TempDir()}
		inst := InstanceRestore{DestPort: 30000, Slots: "0-16383"}
		conf := confFile(host.InstanceDir(inst.DestPort))
		_ = os.MkdirAll(filepath.Dir(conf), 0755)
		_ = os.WriteFile(conf, []byte("cluster-enabled no\n"), 0644)
		r := &plusRestorer{Job: Job{DestIP: "2.2.2.2", SaveDir: t.TempDir(), UnpackDir: t.TempDir(), Host: host},
			cluster: cluster}

		_ = r.setClusterConf([]InstanceRestore{inst})
		p := newHostReport("2.2.2.2", "tendisplus", []InstanceRestore{inst}).port(inst.DestPort)
		if err := r.replayAndMark(inst, p, nil, time.Time{}, make(chan struct{}, 1)); err != nil {
			t.Fatalf("cluster=%v: %v", cluster, err)
		}

		raw, _ := os.ReadFile(conf)
		if got := strings.Contains(string(raw), "cluster-enabled yes"); got != cluster {
			t.Fatalf("cluster=%v: conf rendered for a cluster: %v\n%s", cluster, got, raw)
		}
		if got := len(assigned) == 1; got != cluster {
			t.Fatalf("cluster=%v: slots assigned for %v", cluster, assigned)
		}
		if !IsDone(host.InstanceDir(inst.DestPort), r.fingerprint(inst)) {
			t.Fatalf("cluster=%v: port not marked done", cluster)
		}
	}
}

// portReplayer is one port's instance, shared by the connections of its kvstores.
type portReplayer struct {
	mu   sync.Mutex
	pos  map[int]uint64
	fail uint64
	drop uint64
}

func (f *portReplayer) BinlogPos(kvstore int) (uint64, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.pos[kvstore], nil
}

func (f *portReplayer) execBatch(cmds [][]string) ([]error, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	replies := make([]error, len(cmds))
	for i, args := range cmds {
		kvstore, _ := strconv.Atoi(args[1])
		id, _ := binlogIDFromKey(args[2])
		if id == f.fail {
			replies[i] = fmt.Errorf("ERR apply failed")
			continue
		}
		if id != f.drop {
			f.pos[kvstore] = id
		}
	}
	return replies, nil
}

// scriptTool stands in for binlog_tool, telling the port and kvstore from the replay work dir.
func scriptTool(t *testing.T, run func(port, kvstore int, startPos uint64, onLine func(string) error) error) func() {
	t.Helper()
	binlogToolFn = func(logFile string, startPos uint64, _ int64, onLine func(string) error) (time.Duration, error) {
		var port, kvstore int
		if _, err := fmt.Sscanf(filepath.Base(filepath.Dir(logFile)), "binlog_replay_%d_%d", &port,
			&kvstore); err != nil {
			t.Errorf("work dir of %s: %v", logFile, err)
		}
		return 0, run(port, kvstore, startPos, onLine)
	}
	return func() { binlogToolFn = runBinlogTool }
}

// plusPorts sets up a restorer whose ports are pending, each kvstore holding binlogpos 100 and
// one binlog file to replay.
func plusPorts(t *testing.T, kvstores map[int]int, fake map[int]*portReplayer) (*plusRestorer,
	map[int]map[int][]string, func()) {
	t.Helper()
	r := &plusRestorer{Job: Job{DestIP: "2.2.2.2", SaveDir: t.TempDir(), UnpackDir: t.TempDir(),
		Host: dirHost{root: t.TempDir()}}}
	chains := map[int]map[int][]string{}
	for port, n := range kvstores {
		if fake[port] == nil {
			fake[port] = &portReplayer{}
		}
		fake[port].pos = map[int]uint64{}
		chains[port] = map[int][]string{}
		for kvstore := 0; kvstore < n; kvstore++ {
			fake[port].pos[kvstore] = 100
			chains[port][kvstore] = gzipBinlogs(t, t.TempDir(), "binlog-a.log")
		}
		instDir := r.Host.InstanceDir(port)
		_ = os.MkdirAll(instDir, 0755)
		if err := MarkPending(instDir, r.fingerprint(InstanceRestore{DestPort: port})); err != nil {
			t.Fatal(err)
		}
	}
	dialPlusFn = func(_ string, port int) (plusReplayer, func(), error) { return fake[port], func() {}, nil }
	return r, chains, func() { dialPlusFn = dialPlus }
}

func (r *plusRestorer) replayPort(port int, chains map[int][]string, slots chan struct{}) error {
	inst := InstanceRestore{DestPort: port}
	p := newHostReport(r.DestIP, "tendisplus", []InstanceRestore{inst}).port(port)
	return r.replayAndMark(inst, p, chains, time.Time{}, slots)
}

func TestPlusReplayFailureStopsOnlyItsPort(t *testing.T) {
	fake := map[int]*portReplayer{}
	r, chains, restore := plusPorts(t, map[int]int{30000: 2, 30001: 1}, fake)
	defer restore()
	failing := make(chan struct{})
	const endless = 1 << 20
	sent := 0
	defer scriptTool(t, func(port, kvstore int, start uint64, onLine func(string) error) error {
		switch {
		case port == 30000 && kvstore == 0:
			defer close(failing)
			if err := onLine(restoreLine(0, start)); err != nil {
				return err
			}
			return fmt.Errorf("binlog_tool failed")
		case port == 30000:
			<-failing
			for id := start; id < start+endless; id++ {
				if err := onLine(restoreLine(kvstore, id)); err != nil {
					return err
				}
				sent++
			}
			return nil
		default:
			for id := start; id < start+5; id++ {
				if err := onLine(restoreLine(kvstore, id)); err != nil {
					return err
				}
			}
			return nil
		}
	})()

	slots := make(chan struct{}, 3)
	errs := map[int]error{}
	var mu sync.Mutex
	var wg sync.WaitGroup
	for port := range chains {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			err := r.replayPort(port, chains[port], slots)
			mu.Lock()
			errs[port] = err
			mu.Unlock()
		}(port)
	}
	wg.Wait()

	if err := errs[30000]; err == nil || !strings.Contains(err.Error(), "binlog_tool failed") || failedInFlight(err) {
		t.Fatalf("port 30000: %v", err)
	}
	if sent >= endless {
		t.Fatal("kvstore 1 of the failed port replayed to the end")
	}
	if !IsPending(r.Host.InstanceDir(30000), r.fingerprint(InstanceRestore{DestPort: 30000})) {
		t.Fatal("a failure between batches must keep the port resumable")
	}
	if errs[30001] != nil || fake[30001].pos[0] != 105 ||
		!IsDone(r.Host.InstanceDir(30001), r.fingerprint(InstanceRestore{DestPort: 30001})) {
		t.Fatalf("port 30001: err=%v pos=%d", errs[30001], fake[30001].pos[0])
	}
}

func TestPlusReplayWaitingKvstoresNeverStartAfterAFailure(t *testing.T) {
	r, chains, restore := plusPorts(t, map[int]int{30000: 3}, map[int]*portReplayer{})
	defer restore()
	var mu sync.Mutex
	calls := 0
	defer scriptTool(t, func(int, int, uint64, func(string) error) error {
		mu.Lock()
		calls++
		mu.Unlock()
		return fmt.Errorf("binlog_tool failed")
	})()
	if err := r.replayPort(30000, chains[30000], make(chan struct{}, 1)); err == nil {
		t.Fatal("want error")
	}
	if calls != 1 {
		t.Fatalf("binlog_tool ran %d times, want only the first kvstore", calls)
	}
}

func TestPlusReplayRedoesThePortOnABinlogposMismatch(t *testing.T) {
	cases := map[string]*portReplayer{
		"error reply":        {fail: 102},
		"binlogpos misses":   {drop: 103},
		"id not after start": {},
	}
	for name, fake := range cases {
		r, chains, restore := plusPorts(t, map[int]int{30000: 1}, map[int]*portReplayer{30000: fake})
		ids := []uint64{101, 102, 103}
		if name == "id not after start" {
			ids = []uint64{99}
		}
		resetTool := scriptTool(t, func(_, kvstore int, _ uint64, onLine func(string) error) error {
			for _, id := range ids {
				if err := onLine(restoreLine(kvstore, id)); err != nil {
					return err
				}
			}
			return nil
		})
		err := r.replayPort(30000, chains[30000], make(chan struct{}, 1))
		resetTool()
		restore()
		instDir := r.Host.InstanceDir(30000)
		if !failedInFlight(err) || IsPending(instDir, r.fingerprint(InstanceRestore{DestPort: 30000})) {
			t.Fatalf("%s: err=%v, the port must restore the full backup again", name, err)
		}
	}
}

func TestPlusMemoryReadsCachesFromConf(t *testing.T) {
	conf := filepath.Join(t.TempDir(), "redis.conf")
	_ = os.WriteFile(conf, []byte("rocks.blockcachemb 1024\nrocks.write_buffer_size 1048576\nkvstorecount 10\n"), 0644)
	if got, want := PlusMemory(conf), int64(1024<<20+10*2*1048576); got != want {
		t.Fatalf("got %d, want %d", got, want)
	}
}
