package rollback

import (
	"compress/gzip"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

func touch(t *testing.T, dir string, names ...string) {
	t.Helper()
	for _, name := range names {
		if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0644); err != nil {
			t.Fatal(err)
		}
	}
}

func ssdInstance(names ...string) InstanceRestore {
	return InstanceRestore{
		SourceIP:          "1.1.1.1",
		SourcePort:        30000,
		DestPort:          30000,
		BinlogRange:       BinlogRange{FirstIndex: 10, LastIndex: 12},
		BinlogCount:       len(names),
		BinlogFingerprint: BinlogFingerprint(names),
	}
}

var chain = []string{
	"binlog-1.1.1.1-30000-0000010-20260101000000.log.zst",
	"binlog-1.1.1.1-30000-0000011-20260101010000.log.zst",
	"binlog-1.1.1.1-30000-0000012-20260101020000.log.zst",
}

func TestLocalBinlogsMatchesPlanInIndexOrder(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, chain[2], chain[0], chain[1])
	// Other instances, out-of-range indexes and tendisplus names share the dir and must be ignored.
	touch(t, dir,
		"binlog-2.2.2.2-30000-0000011-20260101010000.log.zst",
		"binlog-1.1.1.1-30001-0000011-20260101010000.log.zst",
		"binlog-1.1.1.1-30000-0000013-20260101030000.log.zst",
		"binlog-1.1.1.1-30000-7-0000011-20260101010000.log.zst",
	)
	files, _, err := LocalBinlogs(dir, ssdInstance(chain...), nil)
	if err != nil {
		t.Fatal(err)
	}
	for i, f := range files {
		if filepath.Base(f) != chain[i] {
			t.Fatalf("files[%d]=%s, want %s", i, f, chain[i])
		}
	}
}

func TestLocalBinlogsAcceptsLegacyNamesWithoutIP(t *testing.T) {
	dir := t.TempDir()
	names := []string{"binlog-30000-0000010-20260101000000.log.lzo", "binlog-30000-0000011-20260101010000.log.lzo"}
	touch(t, dir, names...)
	inst := ssdInstance(names...)
	inst.BinlogRange.LastIndex = 11
	if _, _, err := LocalBinlogs(dir, inst, nil); err != nil {
		t.Fatal(err)
	}
}

func TestLocalBinlogsReportsMissingAndDuplicate(t *testing.T) {
	cases := map[string]struct {
		files []string
		want  string
	}{
		"missing":   {chain[:2], "missing [12]"},
		"duplicate": {append([]string{"binlog-1.1.1.1-30000-0000011-20260101013000.log.zst"}, chain...), "duplicate [11]"},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			touch(t, dir, tc.files...)
			_, _, err := LocalBinlogs(dir, ssdInstance(chain...), nil)
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("err=%v, want %q", err, tc.want)
			}
		})
	}
}

func TestLocalBinlogsAcceptsPlannedGapAndShowsSegmentsOnMismatch(t *testing.T) {
	gapped := []string{chain[0], chain[2]}
	inst := ssdInstance(gapped...)
	inst.BinlogSegments = "[10],[12]"

	dir := t.TempDir()
	touch(t, dir, gapped...)
	if _, _, err := LocalBinlogs(dir, inst, nil); err != nil {
		t.Fatal(err)
	}

	dir = t.TempDir()
	touch(t, dir, chain[0])
	_, _, err := LocalBinlogs(dir, inst, nil)
	if err == nil || !strings.Contains(err.Error(), "want 2 as [10],[12]") {
		t.Fatalf("err=%v", err)
	}
}

func TestLocalBinlogsGapsFollowThePlansAllowance(t *testing.T) {
	gapped := []string{chain[0], chain[2]}
	inst := ssdInstance(gapped...)
	dir := t.TempDir()
	touch(t, dir, gapped...)
	yes, no := true, false

	// an older payload: the plan's digest alone decides, as before
	if files, gaps, err := LocalBinlogs(dir, inst, nil); err != nil || len(files) != 2 || gaps != nil {
		t.Fatalf("nil: files=%v gaps=%v err=%v", files, gaps, err)
	}
	_, _, err := LocalBinlogs(dir, inst, &no)
	if err == nil || !strings.Contains(err.Error(), "1.1.1.1:30000 skip #11") ||
		!strings.Contains(err.Error(), "#11 before "+chain[2]) {
		t.Fatalf("false: err=%v", err)
	}
	files, gaps, err := LocalBinlogs(dir, inst, &yes)
	if err != nil || len(files) != 2 || fmt.Sprint(gaps) != "[11]" {
		t.Fatalf("true: files=%v gaps=%v err=%v", files, gaps, err)
	}
	// a contiguous chain passes either way
	dir = t.TempDir()
	touch(t, dir, chain...)
	if _, gaps, err := LocalBinlogs(dir, ssdInstance(chain...), &no); err != nil || gaps != nil {
		t.Fatalf("contiguous: gaps=%v err=%v", gaps, err)
	}
}

func TestLocalBinlogsRejectsHeadGapAndRepeatsWhenChecked(t *testing.T) {
	yes := true
	dir := t.TempDir()
	touch(t, dir, chain...)
	inst := ssdInstance(chain...)
	inst.BinlogRange.FirstIndex = 9
	no := false
	_, _, err := LocalBinlogs(dir, inst, &no)
	if err == nil || !strings.Contains(err.Error(), "#9 before "+chain[0]) {
		t.Fatalf("head: err=%v", err)
	}

	repeated := append([]string{chain[0], chain[1], "binlog-1.1.1.1-30000-0000011-20260101013000.log.zst"}, chain[2])
	dir = t.TempDir()
	touch(t, dir, repeated...)
	_, _, err = LocalBinlogs(dir, ssdInstance(repeated...), &yes)
	if err == nil || !strings.Contains(err.Error(), "repeat index #11") {
		t.Fatalf("repeat: err=%v", err)
	}
}

func TestIndexRanges(t *testing.T) {
	cases := map[string][]int64{
		"#11":                          {11},
		"#11,#15":                      {11, 15},
		"#31-33,#40":                   {31, 32, 33, 40},
		"#1,#3,#5,#7,#9,...(+2)":       {1, 3, 5, 7, 9, 11, 12},
		"#1-2,#4,#6,#8,#10-11,...(+1)": {1, 2, 4, 6, 8, 10, 11, 13},
	}
	for want, indexes := range cases {
		if got := indexRanges(indexes); got != want {
			t.Fatalf("%v: got %s, want %s", indexes, got, want)
		}
	}
}

func TestLocalBinlogsRejectsSameCountDifferentFiles(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, chain[0], chain[1], "binlog-1.1.1.1-30000-0000012-20260101029999.log.zst")
	if _, _, err := LocalBinlogs(dir, ssdInstance(chain...), nil); err == nil {
		t.Fatal("want fingerprint mismatch")
	}
}

func TestLocalBinlogsNoneExpected(t *testing.T) {
	files, _, err := LocalBinlogs(t.TempDir(), InstanceRestore{DestPort: 30000}, nil)
	if err != nil || files != nil {
		t.Fatalf("files=%v err=%v", files, err)
	}
}

func TestBinlogFingerprintIsOrderSensitive(t *testing.T) {
	if BinlogFingerprint(chain) == BinlogFingerprint([]string{chain[1], chain[0], chain[2]}) {
		t.Fatal("fingerprint must follow index order")
	}
	// The planner computes sha256("a\nb") for the same chain.
	if got := BinlogFingerprint([]string{"a", "b"}); got != "7e18f737311b2dc3b2f269dd78396b0351f14fb66efa879f768cb23181883c78" {
		t.Fatalf("got %s", got)
	}
}

func TestFullStartPos(t *testing.T) {
	cases := map[string]uint64{
		"100-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203-2521252164.tar":    2521252164,
		"100-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203-77.split.001":      77,
		"/data/dbbak/100-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203-9.tar": 9,
		"100-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203.tar":               0,
	}
	for name, want := range cases {
		got, err := fullStartPos([]string{name})
		if want == 0 {
			if err == nil {
				t.Fatalf("%s: want error, got %d", name, got)
			}
			continue
		}
		if err != nil || got != want {
			t.Fatalf("%s: got %d err=%v, want %d", name, got, err, want)
		}
	}
}

func TestSSDRestoreToolByMedia(t *testing.T) {
	cases := map[string]string{
		"redis-2.8.17-rocksdb-v1.2.20.tar.gz": "rr_restore_backup %s %s 1",
		"redis-2.8.17-rocksdb-v1.3.10.tar.gz": "tredisrestore %s %s",
	}
	for media, want := range cases {
		got, err := ssdRestoreTool(media)
		if err != nil || !strings.HasSuffix(got, want) {
			t.Fatalf("%s: got %q err=%v", media, got, err)
		}
	}
	if _, err := ssdRestoreTool("redis-2.8.17-rocksdb-v2.0.1.tar.gz"); err == nil {
		t.Fatal("want error for unknown media")
	}
}

func TestSSDBackupRoot(t *testing.T) {
	work := t.TempDir()
	root := filepath.Join(work, "100-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203-9")
	if err := os.MkdirAll(filepath.Join(root, "meta"), 0755); err != nil {
		t.Fatal(err)
	}
	if got, err := ssdBackupRoot(work); err != nil || got != root {
		t.Fatalf("got %s err=%v", got, err)
	}
	touch(t, filepath.Join(root, "meta"), "2")
	if _, err := ssdBackupRoot(work); err == nil {
		t.Fatal("want error for multi-version backup")
	}
	if _, err := ssdBackupRoot(t.TempDir()); err == nil {
		t.Fatal("want error for empty work dir")
	}
}

func TestSSDDataDirFromConf(t *testing.T) {
	inst := t.TempDir()
	if got := ssdDataDir(inst); got != filepath.Join(inst, "data") {
		t.Fatalf("fallback got %s", got)
	}
	conf := "# dir /nope\ndir /data1/redis/30000/data\nport 30000\n"
	if err := os.WriteFile(filepath.Join(inst, "redis.conf"), []byte(conf), 0644); err != nil {
		t.Fatal(err)
	}
	if got := ssdDataDir(inst); got != "/data1/redis/30000/data" {
		t.Fatalf("got %s", got)
	}
}

func TestReplyStatsClassifiesErrorsByPrefix(t *testing.T) {
	var st replyStats
	for i := 0; i < 6; i++ {
		st.Lines++
		st.record(expectedReplyError+" in setex", `"setex" "k"`)
	}
	st.Lines += 3
	st.record("WRONGTYPE Operation against a key holding the wrong kind of value", `"lpush" "s"`)
	st.record("ERR unknown command 'failedset'", `"set" "k"`)
	if st.Lines != 9 || st.Errors != 8 || st.Expected != 6 {
		t.Fatalf("st=%+v", st)
	}
	wantKinds := map[string]int{expectedReplyError: 6, "WRONGTYPE": 1, "ERR unknown command": 1}
	if fmt.Sprint(st.Kinds) != fmt.Sprint(wantKinds) {
		t.Fatalf("kinds=%v, want %v", st.Kinds, wantKinds)
	}
	samples := st.samples()
	if len(samples) != 2 || !strings.Contains(samples[0], "WRONGTYPE") || !strings.Contains(samples[1], "failedset") {
		t.Fatalf("attention samples must come first: %q", samples)
	}

	var total replyStats
	total.add(st)
	total.add(st)
	if total.Errors != 16 || total.Expected != 12 || total.Kinds[expectedReplyError] != 12 ||
		len(total.samples()) != replyErrorSamples {
		t.Fatalf("total=%+v", total)
	}
	if !strings.Contains(total.summary(), "4 need attention, 12 expected") {
		t.Fatalf("summary=%s", total.summary())
	}
}

func TestReplyStatsKeepsExpectedErrorsApart(t *testing.T) {
	var st replyStats
	st.Lines = 1
	st.record("ERR invalid expire time in 'set' command", `"set" "a"`)
	if st.Errors != 1 || st.Expected != 1 || len(st.Samples) != 0 || len(st.samples()) != 1 {
		t.Fatalf("st=%+v", st)
	}
	if !strings.Contains(st.summary(), "0 need attention, 1 expected") {
		t.Fatalf("summary=%s", st.summary())
	}
}

func TestReplayStartPos(t *testing.T) {
	full := []string{"100-TENDISSSD-FULL-slave-1.1.1.1-30002-20261014-050012-33886.tar"}
	noSeq := []string{"100-TENDISSSD-FULL-slave-1.1.1.1-30002-20261014-050012.tar"}
	seq := func(v uint64, err error) func() (uint64, error) {
		return func() (uint64, error) { return v, err }
	}
	down := fmt.Errorf("connection refused")
	cases := map[string]struct {
		endSeq func() (uint64, error)
		files  []string
		want   uint64
	}{
		"restored end seq equals name":    {seq(33886, nil), full, 33887},
		"restored end seq ahead of name":  {seq(33890, nil), full, 33891},
		"restored end seq behind name":    {seq(33000, nil), full, 33887},
		"binlogsize fails, use name":      {seq(0, down), full, 33887},
		"binlogsize returns 0, use name":  {seq(0, nil), full, 33887},
		"name has no seq, use binlogsize": {seq(33886, nil), noSeq, 33887},
	}
	for name, tc := range cases {
		got, err := replayStartPos(portLog{}, tc.endSeq, tc.files)
		if err != nil || got != tc.want {
			t.Fatalf("%s: got %d err=%v, want %d", name, got, err, tc.want)
		}
	}
	if _, err := replayStartPos(portLog{}, seq(0, down), noSeq); err == nil {
		t.Fatal("want error when neither source has a seq")
	}
}

func TestReplayEndIncludesRecoverAtSecond(t *testing.T) {
	recoverAt := time.Date(2026, 10, 1, 12, 0, 0, 0, time.Local)
	if got, want := replayEndMs(recoverAt), recoverAt.UnixMilli()+1000; got != want {
		t.Fatalf("got %d, want %d", got, want)
	}
}

func TestParseSSDHeartbeat(t *testing.T) {
	beat, dbsize, err := parseSSDHeartbeat("k", []interface{}{"1702415993", "1234"})
	if err != nil || beat.Unix() != 1702415993 || dbsize != 1234 {
		t.Fatalf("seconds: beat=%v dbsize=%d err=%v", beat, dbsize, err)
	}
	if beat, _, err = parseSSDHeartbeat("k", []interface{}{"1702415993123", nil}); err != nil ||
		beat.UnixMilli() != 1702415993123 {
		t.Fatalf("milliseconds: beat=%v err=%v", beat, err)
	}
	if beat, dbsize, err = parseSSDHeartbeat("k", []interface{}{nil, nil}); err != nil || !beat.IsZero() ||
		dbsize != -1 {
		t.Fatalf("none: beat=%v dbsize=%d err=%v", beat, dbsize, err)
	}
	for _, bad := range [][]interface{}{{"not a time", "1"}, {"1"}, nil} {
		if _, _, err = parseSSDHeartbeat("k", bad); err == nil {
			t.Fatalf("%v: want error", bad)
		}
	}
}

func TestSSDHeartbeatCheckOnlyWarns(t *testing.T) {
	defer func() { ssdReplayFn = (*ssdRestorer).replay }()
	recoverAt := time.Date(2026, 10, 30, 16, 5, 0, 0, time.Local)
	cases := map[string]struct {
		beat    time.Time
		err     error
		binlogs []string
		warn    string
	}{
		"within":     {beat: recoverAt.Add(-9 * time.Minute), binlogs: []string{"binlog"}},
		"outside":    {beat: recoverAt.Add(11 * time.Minute), binlogs: []string{"binlog"}, warn: "is more than 10m0s"},
		"none":       {binlogs: []string{"binlog"}},
		"read error": {err: fmt.Errorf("mget failed"), binlogs: []string{"binlog"}, warn: "not read: mget failed"},
		"full only":  {beat: recoverAt.Add(-time.Hour), warn: "is more than 10m0s"},
	}
	for name, tc := range cases {
		logs := captureLogs(t)
		r := ssdRestorerFor(t, dirHost{root: t.TempDir()})
		var keys []string
		ssdHeartbeatFn = func(ip string, port int, timeKey, dbsizeKey string) (time.Time, int64, error) {
			keys = []string{fmt.Sprintf("%s:%d", ip, port), timeKey, dbsizeKey}
			return tc.beat, 42, tc.err
		}
		ssdReplayFn = func(_ *ssdRestorer, _ portLog, p *portReport, _ InstanceRestore, _ time.Time,
			binlogs []string) error {
			p.replayed(len(binlogs), replyStats{})
			p.setSSD(ssdReplayReport{startSeq: 11, firstSeq: 11, lastSeq: 20, lastFile: "binlog"})
			return nil
		}
		inst := InstanceRestore{SourceIP: "1.1.1.1", SourcePort: 30000, DestPort: 30000,
			FullFiles: []string{"full.tar"}}
		h := newHostReport(r.DestIP, engineSSD, []InstanceRestore{inst})
		if err := r.replayAndMark(inst, h.port(30000), tc.binlogs, recoverAt); err != nil ||
			!IsDone(r.Host.InstanceDir(30000), r.fingerprint(inst)) {
			t.Fatalf("%s: a heartbeat must never fail the port: err=%v", name, err)
		}
		h.port(30000).finish(nil)
		if want := "2.2.2.2:30000 1.1.1.1:30000:time 1.1.1.1:30000:0:dbsize"; strings.Join(keys, " ") != want {
			t.Fatalf("%s: read %v, want %s", name, keys, want)
		}

		text := h.diagText(h.port(30000), "")
		beat := "-"
		if !tc.beat.IsZero() && tc.err == nil {
			beat = tc.beat.Format("15:04:05")
		}
		if len(tc.binlogs) > 0 {
			if row := fmt.Sprintf("  %4d %10d -> %-10d %8s", 1, 11, 20, beat); !strings.Contains(text, row) {
				t.Fatalf("%s: diag lacks %q:\n%s", name, row, text)
			}
		} else if !strings.Contains(text, "heartbeat "+beat+"; source dbsize 42") {
			t.Fatalf("%s: diag lacks the heartbeat:\n%s", name, text)
		}
		warned := false
		for _, e := range logs() {
			msg := strings.ReplaceAll(e.msg, "\n"+wrapIndent, " ")
			warned = warned || e.level == levelWarn && strings.Contains(msg, tc.warn)
		}
		if tc.warn == "" {
			if strings.Contains(text, "heartbeat warn") {
				t.Fatalf("%s: unexpected warning:\n%s", name, text)
			}
		} else if !warned || !strings.Contains(text, " heartbeat warn: ") || !strings.Contains(text, tc.warn) {
			t.Fatalf("%s: want warning %q, logged=%v, diag:\n%s", name, tc.warn, warned, text)
		}
	}
}

func TestRetryWhileLoading(t *testing.T) {
	loading := errors.New(consts.REDISLOADDATAINFO)
	wrong := errors.New("ERR wrong")
	const interval = 10 * time.Millisecond
	cases := map[string]struct {
		errs  []error
		end   time.Duration
		calls int
		err   error
	}{
		"loaded later":   {errs: []error{loading, loading, nil}, end: time.Second, calls: 3},
		"loading to end": {errs: []error{loading, loading, loading}, end: 15 * time.Millisecond, calls: 2, err: loading},
		"other error":    {errs: []error{wrong, nil}, end: time.Second, calls: 1, err: wrong},
		"loaded":         {errs: []error{nil}, end: time.Second, calls: 1},
	}
	for name, tc := range cases {
		calls := 0
		vals, err := retryWhileLoading(func() ([]interface{}, error) {
			e := tc.errs[calls]
			calls++
			if e != nil {
				return nil, e
			}
			return []interface{}{"1", "2"}, nil
		}, time.Now().Add(tc.end), interval)
		if calls != tc.calls || err != tc.err || (err == nil && len(vals) != 2) {
			t.Fatalf("%s: calls=%d vals=%v err=%v, want calls=%d err=%v", name, calls, vals, err, tc.calls, tc.err)
		}
	}
}

func TestNewDispatchesByClusterType(t *testing.T) {
	cases := map[string]string{
		"RedisInstance":              "*rollback.cacheRestorer",
		"PredixyRedisCluster":        "*rollback.cacheRestorer cluster",
		"TwemproxyTendisSSDInstance": "*rollback.ssdRestorer",
		"PredixyTendisplusCluster":   "*rollback.plusRestorer cluster",
	}
	for dbType, want := range cases {
		r, err := New(dbType, Job{})
		if err != nil {
			t.Fatalf("%s: %v", dbType, err)
		}
		got := fmt.Sprintf("%T", r)
		switch v := r.(type) {
		case *cacheRestorer:
			if v.cluster {
				got += " cluster"
			}
		case *plusRestorer:
			if v.cluster {
				got += " cluster"
			}
		}
		if got != want {
			t.Fatalf("%s: got %s, want %s", dbType, got, want)
		}
	}
	// Tendisplus types the flow does not accept yet.
	for _, dbType := range []string{"TendisplusCluster", "TendisplusInstance", "TwemproxyTendisplusInstance",
		"PredixyTendisplusInstance"} {
		if _, err := New(dbType, Job{}); err == nil {
			t.Fatalf("%s: want error until the flow accepts it", dbType)
		}
	}
}

func TestInstanceFingerprintCoversBinlogs(t *testing.T) {
	full := InstanceRestore{FullFiles: []string{"b.tar", "a.tar"}}
	if full.Fingerprint() != "a.tar,b.tar" {
		t.Fatalf("cache fingerprint changed: %s", full.Fingerprint())
	}
	withBinlog := full
	withBinlog.BinlogFingerprint = "abc"
	if withBinlog.Fingerprint() != "a.tar,b.tar|abc" {
		t.Fatalf("got %s", withBinlog.Fingerprint())
	}
}

// ssdBinlogOf writes one binlog holding records sets from seq 100 on.
func ssdBinlogOf(t *testing.T, records int) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "binlog-1.1.1.1-30000-0000001-20260101000000.log.gz")
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	w := gzip.NewWriter(f)
	for i := 0; i < records; i++ {
		seq := int64(100 + i)
		_, _ = w.Write(ssdRecordBytes(seq, logKSET, 0, 0, 1000, ssdPlainKey(fmt.Sprintf("k%d", seq)), []byte("v"), nil))
	}
	_ = w.Close()
	_ = f.Close()
	return path
}

// spinExec burns delay of the caller's CPU per batch and answers every command normally.
type spinExec struct{ delay time.Duration }

func (s spinExec) execBatch(cmds [][]string) ([]error, error) {
	for begin := time.Now(); time.Since(begin) < s.delay; {
	}
	return make([]error, len(cmds)), nil
}

func TestSSDReplayBooksDecodeAndBatchCPU(t *testing.T) {
	p := newHostReport("2.2.2.2", engineSSD, []InstanceRestore{{DestPort: 30000}}).port(30000)
	// 20 batches of pipeBatchCmds
	err := replayFiles(newPortLog(30000), p, spinExec{delay: 10 * time.Millisecond},
		[]string{ssdBinlogOf(t, 20*pipeBatchCmds)}, ssdReplayReport{startSeq: 100, endMs: 1 << 62})
	if err != nil {
		t.Fatal(err)
	}
	apply, decode := p.cpu[stageApply], p.cpu[stageDecode]
	if apply < 100*time.Millisecond {
		t.Fatalf("apply cpu %v: the batches' client CPU is apply's", apply)
	}
	if decode <= 0 || decode >= apply {
		t.Fatalf("decode cpu %v, apply %v: decode is the Go decoder's alone", decode, apply)
	}
}

func TestSSDReplayBooksTheLastFlushAsApply(t *testing.T) {
	p := newHostReport("2.2.2.2", engineSSD, []InstanceRestore{{DestPort: 30000}}).port(30000)
	delay := 100 * time.Millisecond
	// Fewer records than a batch, so the only batch goes out in the flush after decoding.
	err := replayFiles(newPortLog(30000), p, spinExec{delay: delay},
		[]string{ssdBinlogOf(t, 10)}, ssdReplayReport{startSeq: 100, endMs: 1 << 62})
	if err != nil {
		t.Fatal(err)
	}
	if p.durations[stageApply] < delay || p.cpu[stageApply] < delay/2 {
		t.Fatalf("apply wall %v cpu %v: the last flush is apply's", p.durations[stageApply], p.cpu[stageApply])
	}
	if p.durations[stageDecode] >= delay/2 || p.cpu[stageDecode] >= delay/2 {
		t.Fatalf("decode wall %v cpu %v took in the last flush", p.durations[stageDecode], p.cpu[stageDecode])
	}
}

func TestRestoreRocksdbReportsTheToolsCPU(t *testing.T) {
	ssdBinDir = t.TempDir()
	defer func() { ssdBinDir = filepath.Join(consts.UsrLocal, "redis", "bin") }()
	script := "#!/bin/bash\ni=0; while [ $i -lt 100000 ]; do i=$((i+1)); done\necho 'ERR: restore broke'\n"
	if err := os.WriteFile(filepath.Join(ssdBinDir, "tredisrestore"), []byte(script), 0755); err != nil {
		t.Fatal(err)
	}
	work := t.TempDir()
	cpu, err := restoreRocksdb("redis-2.8.17-rocksdb-v1.3.10.tar.gz", t.TempDir(), t.TempDir(), work)
	if err == nil || !strings.Contains(err.Error(), "ERR: restore broke") || cpu <= 0 {
		t.Fatalf("cpu=%v err=%v", cpu, err)
	}
	if _, err = os.Stat(filepath.Join(work, "restore.out")); err != nil {
		t.Fatalf("tool output not kept: %v", err)
	}
}

func TestSSDFailingBinlogGoesToTheDetailFile(t *testing.T) {
	p := newHostReport("2.2.2.2", engineSSD, []InstanceRestore{{DestPort: 30000}}).port(30000)
	p.detailPath = filepath.Join(t.TempDir(), "rollback_detail_30000.log")
	exec := &fakeExec{reply: func([]string) error { return errors.New("ERR unknown command 'set'") }}
	err := replayFiles(newPortLog(30000), p, exec, ssdBinlogs(t, 1), ssdReplayReport{startSeq: 100, endMs: 1 << 62})
	if err == nil || !strings.Contains(err.Error(), "all 2 replies are errors") {
		t.Fatalf("err=%v", err)
	}
	_ = p.closeDetail()
	raw, _ := os.ReadFile(p.detailPath)
	containsAll(t, string(raw),
		"  error [binlog-1.1.1.1-30000-0000001-20260101000000.log.gz] seq=100 ts="+
			time.UnixMilli(1000).Format("2006-01-02 15:04:05.000")+" (error) ERR unknown command 'set' <- ",
		"ERROR binlog-1.1.1.1-30000-0000001-20260101000000.log.gz: all 2 replies are errors",
	)
}

func TestDetailRepliesAreCapped(t *testing.T) {
	p := newHostReport("2.2.2.2", engineSSD, []InstanceRestore{{DestPort: 30000}}).port(30000)
	p.detailPath = filepath.Join(t.TempDir(), "rollback_detail_30000.log")
	for i := 0; i < detailMaxReplies+3; i++ {
		p.detailReply("  error %d", i)
	}
	p.noteOmittedReplies()
	_ = p.closeDetail()
	raw, _ := os.ReadFile(p.detailPath)
	detail := string(raw)
	if n := strings.Count(detail, "  error "); n != detailMaxReplies ||
		!strings.HasSuffix(detail, "... (3 more error replies omitted)\n") {
		t.Fatalf("%d error lines, tail %q", n, detail[len(detail)-60:])
	}
}

func TestSSDDiagSamplesStayOnOneLine(t *testing.T) {
	h := newHostReport("2.2.2.2", engineSSD, []InstanceRestore{{DestPort: 30000}})
	p := h.port(30000)
	var st replyStats
	for i := 0; i < 5; i++ {
		st.Lines++
		st.record("WRONGTYPE Operation against a key holding the wrong kind of value",
			commandPreview([]string{"lpush", strings.Repeat("a_very_long_key_name_", 5) + fmt.Sprint(i), "v"}))
	}
	p.replayed(1, st)
	p.finish(nil)
	text := h.diagText(p, "")
	if n := strings.Count(text, "\n  (error) WRONGTYPE"); n != 2 {
		t.Fatalf("%d samples:\n%s", n, text)
	}
	if wrapRecord(text) != text {
		t.Fatalf("diag wraps:\n%s", wrapRecord(text))
	}
}
