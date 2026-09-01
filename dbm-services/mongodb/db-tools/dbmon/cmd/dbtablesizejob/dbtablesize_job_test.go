package dbtablesizejob

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/mongodb/db-tools/dbmon/config"
)

func TestShouldSkipCollection(t *testing.T) {
	cases := []struct {
		name     string
		db       string
		coll     string
		dataSize int64
		wantSkip bool
	}{
		{name: "heartbeat_small", db: "test", coll: "dbmon_heartbeat", dataSize: 100, wantSkip: true},
		{name: "heartbeat_just_under_1m", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes - 1, wantSkip: true},
		{name: "heartbeat_exact_1m", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes, wantSkip: false},
		{name: "heartbeat_large", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes + 1, wantSkip: false},
		{name: "other_coll", db: "test", coll: "other", dataSize: 100, wantSkip: false},
		{name: "other_db", db: "admin", coll: "dbmon_heartbeat", dataSize: 100, wantSkip: false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := shouldSkipCollection(c.db, c.coll, c.dataSize)
			if got != c.wantSkip {
				t.Fatalf("shouldSkipCollection(%q,%q,%d)=%v, want %v",
					c.db, c.coll, c.dataSize, got, c.wantSkip)
			}
		})
	}
}

func TestReportBucket(t *testing.T) {
	cases := []struct {
		name string
		in   string // RFC3339 in +08:00
		want string
	}{
		{name: "1756_to_1750", in: "2026-08-31T17:56:45+08:00", want: "202608311750"},
		{name: "1800_to_1800", in: "2026-08-31T18:00:00+08:00", want: "202608311800"},
		{name: "1700_to_1700", in: "2026-08-31T17:00:01+08:00", want: "202608311700"},
		{name: "1709_to_1700", in: "2026-08-31T17:09:59+08:00", want: "202608311700"},
		{name: "2359_to_2350", in: "2026-08-31T23:59:00+08:00", want: "202608312350"},
		{name: "cross_day_0001", in: "2026-09-01T00:01:00+08:00", want: "202609010000"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			tm, err := time.Parse(time.RFC3339, c.in)
			if err != nil {
				t.Fatal(err)
			}
			got := reportBucket(tm)
			if got != c.want {
				t.Fatalf("reportBucket(%s)=%s, want %s", c.in, got, c.want)
			}
		})
	}
}

func TestCompletedBucketPersist(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, lastBucketFileName)

	got, err := readCompletedBucket(path)
	if err != nil {
		t.Fatal(err)
	}
	if got != "" {
		t.Fatalf("empty file want \"\", got %q", got)
	}

	bucket := "202608311700"
	if err := writeCompletedBucket(path, bucket); err != nil {
		t.Fatal(err)
	}
	got, err = readCompletedBucket(path)
	if err != nil {
		t.Fatal(err)
	}
	if got != bucket {
		t.Fatalf("read=%q, want %q", got, bucket)
	}

	// rewrite
	bucket2 := "202608311710"
	if err := writeCompletedBucket(path, bucket2); err != nil {
		t.Fatal(err)
	}
	got, err = readCompletedBucket(path)
	if err != nil {
		t.Fatal(err)
	}
	if got != bucket2 {
		t.Fatalf("read=%q, want %q", got, bucket2)
	}

	// no leftover tmp
	if _, err := os.Stat(path + ".tmp"); !os.IsNotExist(err) {
		t.Fatalf("tmp file should not exist, err=%v", err)
	}
}

func TestPurgeInstanceBucketRecords(t *testing.T) {
	dir := t.TempDir()
	reportFile := filepath.Join(dir, "dbtablesize-20260901.log")
	lines := []string{
		`{"instance":"1.1.1.1:27017","report_bucket":"202608311700","db":"a","collection":"c1"}`,
		`{"instance":"1.1.1.1:27017","report_bucket":"202608311710","db":"a","collection":"c1"}`,
		`{"instance":"2.2.2.2:27017","report_bucket":"202608311700","db":"b","collection":"c2"}`,
	}
	if err := os.WriteFile(reportFile, []byte(strings.Join(lines, "\n")+"\n"), 0644); err != nil {
		t.Fatal(err)
	}

	if err := purgeInstanceBucketRecords(reportFile, "1.1.1.1:27017", "202608311700"); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(reportFile)
	if err != nil {
		t.Fatal(err)
	}
	got := strings.TrimSpace(string(data))
	want := strings.Join([]string{
		`{"instance":"1.1.1.1:27017","report_bucket":"202608311710","db":"a","collection":"c1"}`,
		`{"instance":"2.2.2.2:27017","report_bucket":"202608311700","db":"b","collection":"c2"}`,
	}, "\n")
	if got != want {
		t.Fatalf("purge result:\n%s\nwant:\n%s", got, want)
	}

	// purge all matching rows leaves empty file
	if err := purgeInstanceBucketRecords(reportFile, "2.2.2.2:27017", "202608311700"); err != nil {
		t.Fatal(err)
	}
	if err := purgeInstanceBucketRecords(reportFile, "1.1.1.1:27017", "202608311710"); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(reportFile)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size() != 0 {
		t.Fatalf("expected empty report file, size=%d", info.Size())
	}
}

func TestNewSizeRecordAggLevelAndBucket(t *testing.T) {
	svr := &config.ConfServerItem{}
	svr.ClusterName = "c1"
	svr.SetName = "c1-s1"
	svr.IP = "1.1.1.1"
	svr.Port = 27017
	rec := newSizeRecord(svr, "db1", "coll1", 1, 2, 3, 4, 5.5, "2026-08-31T17:01:00+08:00", "202608311700")
	if rec.AggLevel != aggLevelShard {
		t.Fatalf("agg_level=%q, want %q", rec.AggLevel, aggLevelShard)
	}
	if rec.ReportBucket != "202608311700" {
		t.Fatalf("report_bucket=%q", rec.ReportBucket)
	}
	if rec.Collection == "" {
		t.Fatal("collection must be non-empty for shard collection rows")
	}
}

// TestBucketGate documents Run() skip rule: completed bucket matches current → skip;
// incomplete (empty / other bucket) → allow retry any minute in the same 10-min window.
func TestBucketGate(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, lastBucketFileName)
	bucket1700 := "202608311700"

	t1700, _ := time.Parse(time.RFC3339, "2026-08-31T17:00:00+08:00")
	t1705, _ := time.Parse(time.RFC3339, "2026-08-31T17:05:30+08:00")
	t1710, _ := time.Parse(time.RFC3339, "2026-08-31T17:10:00+08:00")

	// not completed → any minute in window may run
	for _, tm := range []time.Time{t1700, t1705} {
		completed, err := readCompletedBucket(path)
		if err != nil {
			t.Fatal(err)
		}
		cur := reportBucket(tm)
		if completed == cur {
			t.Fatalf("should allow run at %s before complete", tm)
		}
		if cur != bucket1700 {
			t.Fatalf("bucket=%s, want %s", cur, bucket1700)
		}
	}

	if err := writeCompletedBucket(path, bucket1700); err != nil {
		t.Fatal(err)
	}
	// after complete (incl. "restart" re-read) → skip rest of window
	completed, err := readCompletedBucket(path)
	if err != nil {
		t.Fatal(err)
	}
	if completed != reportBucket(t1705) {
		t.Fatalf("should skip at 17:05 after complete")
	}
	// next bucket may run
	if completed == reportBucket(t1710) {
		t.Fatalf("should not skip new bucket 17:10")
	}
}
