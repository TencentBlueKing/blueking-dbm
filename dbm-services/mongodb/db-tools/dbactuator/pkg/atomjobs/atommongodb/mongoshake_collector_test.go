package atommongodb

import (
	"archive/tar"
	"compress/gzip"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

func testMongoURI(host string) string {
	return strings.Join([]string{"mongodb", "://", "xxxx", ":", "xxxx", "@", host}, "")
}

func TestMongoShakeCaughtUpUsesSourceLSN(t *testing.T) {
	lag, ok := mongoShakeCaughtUp(110, 100, 15)
	if !ok || lag != 10 {
		t.Fatalf("expected caught up lag=10, got lag=%d ok=%t", lag, ok)
	}
	if _, ok = mongoShakeCaughtUp(100, 0, 15); ok {
		t.Fatal("ack 0 must not be caught up")
	}
	if _, ok = mongoShakeCaughtUp(200, 100, 15); ok {
		t.Fatal("lag 100 must not be caught up")
	}
}

func TestShouldLogProgressOncePerMinute(t *testing.T) {
	start := time.Date(2026, 11, 23, 15, 0, 0, 0, time.UTC)
	if !shouldLogProgress(time.Time{}, start) {
		t.Fatal("first sample should log")
	}
	if shouldLogProgress(start, start.Add(59*time.Second)) {
		t.Fatal("59s later should not log")
	}
	if !shouldLogProgress(start, start.Add(time.Minute)) {
		t.Fatal("60s later should log")
	}
}

func TestValidateMongoShakeWorkDir(t *testing.T) {
	if err := validateMongoShakeWorkDir("/data/mongo-dts/mongodtsabc"); err != nil {
		t.Fatal(err)
	}
	if err := validateMongoShakeWorkDir("/tmp/mongodtsabc"); err == nil {
		t.Fatal("expected workDir outside /data/mongo-dts to fail")
	}
}

func TestMongoShakeCaughtUpIdleSource(t *testing.T) {
	if _, ok := mongoShakeCaughtUp(100, 100, 15); !ok {
		t.Fatal("lsn == ack on an idle source should pass the apply-side check")
	}
}

func TestPendingCheckFrom(t *testing.T) {
	work := t.TempDir()
	job := &mongoshakeCollectorJob{param: &mongoshakeCollectorParam{WorkDir: work, LagSeconds: 15}}
	start := primitive.Timestamp{T: 100, I: 2}
	if ts, ok := job.pendingCheckFrom(110, 100, true, start); !ok || ts.T != 116 {
		t.Fatalf("caught up should check from ack+lag+1, got %v %t", ts, ok)
	}
	if _, ok := job.pendingCheckFrom(200, 0, false, start); ok {
		t.Fatal("fetched but not acked must not check source")
	}
	if _, ok := job.pendingCheckFrom(0, 0, false, primitive.Timestamp{}); ok {
		t.Fatal("idle check needs a recorded start ts")
	}
	if ts, ok := job.pendingCheckFrom(0, 0, false, start); !ok || ts.T != 100 || ts.I != 3 {
		t.Fatalf("idle source should check from start ts, got %v %t", ts, ok)
	}
}

func TestParseShakeSourceConf(t *testing.T) {
	h1URI := testMongoURI("h1:27017")
	h2URI := testMongoURI("h2:27017")
	s1URI := testMongoURI("s1:27017")
	conf, err := parseShakeSourceConf("mongo_urls = " + h1URI + "\n" +
		"mongo_s_url =\nmongo_connect_mode = standalone\nfilter.namespace.white = db1;db2.c1\n")
	if err != nil {
		t.Fatal(err)
	}
	if len(conf.Sources) != 1 || conf.Sources[0].URI != h1URI ||
		!conf.Sources[0].Direct || len(conf.Whitelist) != 2 {
		t.Fatalf("unexpected conf %+v", conf)
	}
	conf, err = parseShakeSourceConf("mongo_urls =\nmongo_s_url = " + s1URI + "\n" +
		"mongo_connect_mode = standalone\n")
	if err != nil {
		t.Fatal(err)
	}
	if len(conf.Sources) != 1 || conf.Sources[0].URI != s1URI ||
		conf.Sources[0].Direct || len(conf.Whitelist) != 0 {
		t.Fatalf("unexpected mongos conf %+v", conf)
	}
	conf, err = parseShakeSourceConf("mongo_urls = " + h1URI + ";" + h2URI + "\n" +
		"mongo_s_url =\nmongo_connect_mode = standalone\n")
	if err != nil || len(conf.Sources) != 2 || !conf.Sources[1].Direct {
		t.Fatalf("unexpected multi-source conf %+v err=%v", conf, err)
	}
	if _, err = parseShakeSourceConf("mongo_urls =\n"); err == nil {
		t.Fatal("expected empty source url to fail")
	}
}

func TestOplogNamespaceCondition(t *testing.T) {
	raw, err := bson.MarshalExtJSON(oplogNamespaceCondition([]string{"db1", "db2.c1"}), false, false)
	if err != nil {
		t.Fatal(err)
	}
	text := string(raw)
	for _, expected := range []string{`^db1\\.`, `^db2\\.c1$`, `^db2\\.system\\.buckets\\.c1$`} {
		if !strings.Contains(text, expected) {
			t.Fatalf("namespace condition %s does not contain %s", text, expected)
		}
	}
	allRaw, err := bson.MarshalExtJSON(oplogNamespaceCondition(nil), false, false)
	if err != nil || !strings.Contains(string(allRaw), "admin|config|local") {
		t.Fatalf("unexpected all-user-db condition %s err=%v", allRaw, err)
	}
}

func TestReadReplLagObjectAndArray(t *testing.T) {
	for _, body := range []string{
		`{"replset":"rs0","lsn":{"unix":110,"ts":"472446402560"},"lsn_ack":{"unix":100,"ts":"429496729600"}}`,
		`[{"replset":"rs0","lsn":{"unix":110},"lsn_ack":{"unix":100}},` +
			`{"replset":"rs1","lsn":{"unix":210},"lsn_ack":{"unix":200}}]`,
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
			_, _ = w.Write([]byte(body))
		}))
		repls, err := readReplLags(server.Client(), mustPort(t, server.URL))
		server.Close()
		if err != nil {
			t.Fatal(err)
		}
		if len(repls) == 0 || repls[0].Replset != "rs0" {
			t.Fatalf("unexpected repl response %+v", repls)
		}
	}
}

func TestPostSentinelOptions(t *testing.T) {
	var request map[string]interface{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/sentinel/options" || r.Method != http.MethodPost {
			t.Fatalf("unexpected request %s %s", r.Method, r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Fatal(err)
		}
		_, _ = w.Write([]byte(`{"sentinel":"success"}`))
	}))
	defer server.Close()
	cut := int64(200) << 32
	if err := postSentinelOptions(server.Client(), mustPort(t, server.URL), map[string]interface{}{
		"ExitPoint": cut,
	}); err != nil {
		t.Fatal(err)
	}
	if got := int64(request["ExitPoint"].(float64)); got != cut {
		t.Fatalf("exit point lost precision: got %d want %d", got, cut)
	}
}

func TestCutAppliedAtExactAck(t *testing.T) {
	cut := primitive.Timestamp{T: 200}
	packed := strconv.FormatInt(int64(cut.T)<<32, 10)
	ok, err := cutApplied(
		[]shakeSource{{Replset: "rs0"}},
		map[string]primitive.Timestamp{"rs0": {T: 100}},
		[]shakeRepl{{
			Replset: "rs0",
			LsnAck:  &shakeTime{Unix: 200, TS: packed},
			LsnCkpt: &shakeTime{Unix: 200, TS: packed},
		}},
		cut,
	)
	if err != nil || !ok {
		t.Fatalf("expected exact ack to pass, ok=%t err=%v", ok, err)
	}
}

func TestStartAndStopCollector(t *testing.T) {
	work := t.TempDir()
	pkg := filepath.Join(t.TempDir(), "mongo-dts.tar.gz")
	writeFakeCollectorTar(t, pkg)
	job := &mongoshakeCollectorJob{param: &mongoshakeCollectorParam{
		WorkDir: work,
		PkgPath: pkg,
		Conf:    "id = test\n",
	}}
	sourceOpTimes = func(string) (map[string]primitive.Timestamp, error) {
		return map[string]primitive.Timestamp{"rs0": {T: 100, I: 2}}, nil
	}
	defer func() { sourceOpTimes = sourceOperationTimes }()
	// start() does not check the production workDir regex; Init does.
	if err := job.start(); err != nil {
		t.Fatal(err)
	}
	if timestamps, err := readStartTsMap(work); err != nil ||
		timestamps["rs0"].T != 100 || timestamps["rs0"].I != 2 {
		t.Fatalf("start timestamps not recorded: %v %v", timestamps, err)
	}
	alive, pid := collectorPidAlive(work)
	if !alive || pid <= 0 {
		t.Fatal("collector pid not alive")
	}
	job.param.RemoveConf = true
	if err := job.stop(); err != nil {
		t.Fatal(err)
	}
	if alive, _ = collectorPidAlive(work); alive {
		t.Fatal("collector still alive")
	}
	if _, err := os.Stat(filepath.Join(work, "collector.conf")); !os.IsNotExist(err) {
		t.Fatal("collector.conf should be removed")
	}
}

func writeFakeCollectorTar(t *testing.T, pkg string) {
	t.Helper()
	file, err := os.Create(pkg)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	gz := gzip.NewWriter(file)
	tw := tar.NewWriter(gz)
	body := []byte("#!/bin/sh\nexec sleep 300\n")
	hdr := &tar.Header{Name: "mongo-dts/collector.linux", Mode: 0755, Size: int64(len(body))}
	if err = tw.WriteHeader(hdr); err != nil {
		t.Fatal(err)
	}
	if _, err = tw.Write(body); err != nil {
		t.Fatal(err)
	}
	if err = tw.Close(); err != nil {
		t.Fatal(err)
	}
	if err = gz.Close(); err != nil {
		t.Fatal(err)
	}
}

func mustPort(t *testing.T, rawURL string) int {
	t.Helper()
	// httptest URL is http://127.0.0.1:port
	i := len(rawURL) - 1
	for i >= 0 && rawURL[i] != ':' {
		i--
	}
	port, err := strconv.Atoi(rawURL[i+1:])
	if err != nil {
		t.Fatal(err)
	}
	return port
}
