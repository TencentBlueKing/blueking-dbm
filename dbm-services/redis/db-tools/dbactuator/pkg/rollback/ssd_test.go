package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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
	files, err := LocalBinlogs(dir, ssdInstance(chain...))
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
	if _, err := LocalBinlogs(dir, inst); err != nil {
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
			_, err := LocalBinlogs(dir, ssdInstance(chain...))
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
	if _, err := LocalBinlogs(dir, inst); err != nil {
		t.Fatal(err)
	}

	dir = t.TempDir()
	touch(t, dir, chain[0])
	_, err := LocalBinlogs(dir, inst)
	if err == nil || !strings.Contains(err.Error(), "want 2 as [10],[12]") {
		t.Fatalf("err=%v", err)
	}
}

func TestLocalBinlogsRejectsSameCountDifferentFiles(t *testing.T) {
	dir := t.TempDir()
	touch(t, dir, chain[0], chain[1], "binlog-1.1.1.1-30000-0000012-20260101029999.log.zst")
	if _, err := LocalBinlogs(dir, ssdInstance(chain...)); err == nil {
		t.Fatal("want fingerprint mismatch")
	}
}

func TestLocalBinlogsNoneExpected(t *testing.T) {
	files, err := LocalBinlogs(t.TempDir(), InstanceRestore{DestPort: 30000})
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

func writeOut(t *testing.T, content string) string {
	t.Helper()
	out := filepath.Join(t.TempDir(), "out")
	if err := os.WriteFile(out, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return out
}

func TestReadRepliesSkipsAuthReply(t *testing.T) {
	st, err := readReplies(writeOut(t, "OK\nOK\n(error) ERR wrong\n(integer) 1\n\"v\"\n"))
	if err != nil || st.Lines != 4 || st.Errors != 1 || len(st.Samples) != 1 {
		t.Fatalf("st=%+v err=%v", st, err)
	}
}

func TestReadRepliesFailsOnAuth(t *testing.T) {
	for name, content := range map[string]string{
		"wrong password": "(error) WRONGPASS invalid password\nOK\n",
		"no reply":       "",
	} {
		if _, err := readReplies(writeOut(t, content)); err == nil {
			t.Fatalf("%s: want error", name)
		}
	}
}

func TestReadRepliesCapsSamples(t *testing.T) {
	st, err := readReplies(writeOut(t, "OK\n"+strings.Repeat("(error) BUSYKEY exists\n", 8)))
	if err != nil || st.Lines != 8 || st.Errors != 8 || len(st.Samples) != replyErrorSamples {
		t.Fatalf("st=%+v err=%v", st, err)
	}
	var total replyStats
	total.add(st)
	total.add(st)
	if total.Lines != 16 || total.Errors != 16 || len(total.Samples) != replyErrorSamples {
		t.Fatalf("total=%+v", total)
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

func writeCmd(t *testing.T, content string) string {
	t.Helper()
	cmd := filepath.Join(t.TempDir(), "binlog.log.cmd")
	if err := os.WriteFile(cmd, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return cmd
}

func TestCheckParsedCommandsFailsOnUnknownLogType(t *testing.T) {
	// From ticket 2571128: a DEL of a 210k-member set followed by SET on TendisSSD v1.3.10.
	content := `"sadd" "rb_asyncdel_test" "m1"` + "\n" +
		`"del" "rb_asyncdel_test"` + "\n" +
		"Wrong log type: 17 !!!\n" +
		`failed"set" "rb_asyncdel_after" "1"` + "\n"
	err := checkParsedCommands(writeCmd(t, content))
	if err == nil {
		t.Fatal("want error")
	}
	for _, want := range []string{"1 records of unknown log type [17]", "glued 1 commands", "first at line 3"} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("err=%v, want %q", err, want)
		}
	}
}

func TestCheckParsedCommandsFailsOnGluedLineAlone(t *testing.T) {
	if err := checkParsedCommands(writeCmd(t, `"set" "a" "1"`+"\n"+`failed"set" "b" "1"`)); err == nil {
		t.Fatal("want error for a glued line without a newline at EOF")
	}
}

func TestCheckParsedCommandsAcceptsQuotedCommands(t *testing.T) {
	// Markers inside values or past a long line's first buffer are not line starts.
	long := `"set" "k" "` + strings.Repeat("x", 200*1024) + `failed"` + "\n"
	content := `"set" "Wrong log type: 17" "failed"` + "\n" + long + `"del" "k"` + "\n"
	if err := checkParsedCommands(writeCmd(t, content)); err != nil {
		t.Fatal(err)
	}
	if err := checkParsedCommands(writeCmd(t, "")); err != nil {
		t.Fatal(err)
	}
}

func TestReadRepliesClassifiesErrors(t *testing.T) {
	content := "OK\n" +
		strings.Repeat("(error) ERR invalid expire time in setex\n", 6) +
		"(error) WRONGTYPE Operation against a key holding the wrong kind of value\n" +
		"(error) ERR unknown command 'failedset'\n" +
		"OK\n"
	st, err := readReplies(writeOut(t, content))
	if err != nil {
		t.Fatal(err)
	}
	if st.Lines != 9 || st.Errors != 8 || st.Expected != 6 {
		t.Fatalf("st=%+v", st)
	}
	wantKinds := map[string]int{expectedReplyError: 6, "WRONGTYPE": 1, "ERR unknown command": 1}
	if fmt.Sprint(st.Kinds) != fmt.Sprint(wantKinds) {
		t.Fatalf("kinds=%v, want %v", st.Kinds, wantKinds)
	}
	samples := st.samples()
	if len(samples) != replyErrorSamples || !strings.Contains(samples[0], "WRONGTYPE") ||
		!strings.Contains(samples[1], "failedset") || !strings.Contains(samples[2], expectedReplyError) {
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

func TestReadRepliesOnlyExpectedErrors(t *testing.T) {
	st, err := readReplies(writeOut(t, "OK\nOK\n(error) ERR invalid expire time in 'set' command\n"))
	if err != nil || st.Errors != 1 || st.Expected != 1 || len(st.Samples) != 0 || len(st.samples()) != 1 {
		t.Fatalf("st=%+v err=%v", st, err)
	}
}

func TestReplayEndIncludesRecoverAtSecond(t *testing.T) {
	recoverAt := time.Date(2026, 10, 1, 12, 0, 0, 0, time.Local)
	if got, want := replayEndMs(recoverAt), recoverAt.UnixMilli()+1000; got != want {
		t.Fatalf("got %d, want %d", got, want)
	}
}

func TestAuthLineQuotesPassword(t *testing.T) {
	cases := map[string]string{
		"plain":       "AUTH \"plain\"\n",
		`a"b\c d`:     `AUTH "a\"b\\c d"` + "\n",
		"tab\there\n": `AUTH "tab\x09here\x0a"` + "\n",
	}
	for password, want := range cases {
		if got := authLine(password); got != want {
			t.Fatalf("%q: got %q, want %q", password, got, want)
		}
	}
}

func TestNewDispatchesByClusterType(t *testing.T) {
	cases := map[string]string{
		"RedisInstance":              "*rollback.cacheRestorer",
		"TwemproxyTendisSSDInstance": "*rollback.ssdRestorer",
	}
	for dbType, want := range cases {
		r, err := New(dbType, Job{})
		if err != nil {
			t.Fatalf("%s: %v", dbType, err)
		}
		if got := fmt.Sprintf("%T", r); got != want {
			t.Fatalf("%s: got %s, want %s", dbType, got, want)
		}
	}
	if _, err := New("PredixyTendisplusCluster", Job{}); err == nil {
		t.Fatal("want error for unsupported engine")
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
