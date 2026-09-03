/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package config_test

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"

	"github.com/spf13/viper"
)

func restoreCfg(t *testing.T) {
	t.Helper()
	saved := config.Cfg
	t.Cleanup(func() {
		config.Apply(saved)
	})
}

// TestParse_ClampsSyncInterval covers the three regions of admin.syncInterval: omitted or zero
// means sync is off and must stay off, a positive value below the floor is raised rather than
// rejected, and a sane value passes through untouched.
func TestParse_ClampsSyncInterval(t *testing.T) {
	cases := []struct {
		name     string
		interval string
		want     time.Duration
		enabled  bool
	}{
		{name: "omitted", interval: "", want: 0, enabled: false},
		{name: "zero disables sync", interval: "syncInterval: 0s", want: 0, enabled: false},
		{name: "below floor is clamped", interval: "syncInterval: 1s", want: config.MinSyncInterval, enabled: true},
		{name: "at floor is kept", interval: "syncInterval: 10s", want: config.MinSyncInterval, enabled: true},
		{name: "above floor is kept", interval: "syncInterval: 5m", want: 5 * time.Minute, enabled: true},
		{name: "negative disables sync", interval: "syncInterval: -1s", want: -time.Second, enabled: false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			doc := "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n  " + tc.interval + "\n"
			parsed, err := config.ParseBytes([]byte(doc))
			if err != nil {
				t.Fatalf("parse failed, errmsg: %s", err)
			}
			if parsed.Admin.SyncInterval != tc.want {
				t.Errorf("syncInterval: %s, want: %s", parsed.Admin.SyncInterval, tc.want)
			}
			if parsed.Admin.SyncEnabled() != tc.enabled {
				t.Errorf("syncEnabled: %v, want: %v", parsed.Admin.SyncEnabled(), tc.enabled)
			}
		})
	}
}

// TestParse_SyncNeedsEndpoints keeps an interval without endpoints from being treated as
// enabled: it would tick forever with nowhere to send the request.
func TestParse_SyncNeedsEndpoints(t *testing.T) {
	parsed, err := config.ParseBytes([]byte("name: probe\nadmin:\n  syncInterval: 30s\n"))
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if parsed.Admin.SyncEnabled() {
		t.Error("sync should stay disabled without admin endpoints")
	}
}

// TestApply_KeepsSnapshotInStep guards the invariant background goroutines rely on: whatever
// Apply installs must be visible through Snapshot, which is the only race-free read path.
func TestApply_KeepsSnapshotInStep(t *testing.T) {
	restoreCfg(t)

	next := config.Cfg
	next.ServiceID = "svc-applied"
	config.Apply(next)

	if got := config.Snapshot().ServiceID; got != "svc-applied" {
		t.Fatalf("snapshot did not follow Apply, serviceID: %s", got)
	}
	if config.Cfg.ServiceID != "svc-applied" {
		t.Fatalf("Cfg did not follow Apply, serviceID: %s", config.Cfg.ServiceID)
	}
}

// TestSnapshot_ConcurrentReadsDuringApply is meaningful under -race: the periodic sync
// goroutine reads while hot reload writes, which is exactly the pattern Apply/Snapshot exists
// to make safe.
func TestSnapshot_ConcurrentReadsDuringApply(t *testing.T) {
	restoreCfg(t)

	done := make(chan struct{})
	go func() {
		defer close(done)
		for i := 0; i < 200; i++ {
			_ = config.Snapshot().ServiceID
		}
	}()

	base := config.Cfg
	for i := 0; i < 200; i++ {
		next := base
		next.ServiceID = "svc"
		config.Apply(next)
	}
	<-done
}

// TestParseBytes_MatchesParseFromFile pins the equivalence periodic sync depends on: a
// rendered document is validated in memory with ParseBytes but ends up on disk and is reloaded
// with Parse. If the two paths applied different defaults or normalization, the config compared
// before writing would differ from the one that actually takes effect.
func TestParseBytes_MatchesParseFromFile(t *testing.T) {
	restoreCfg(t)

	doc := []byte(`
name: probe
serviceID: svc-1
harvester:
  mysql:
    user: u
    password: p
    interval: 10s
    timeout: 1s
    endpoints:
      - ip: 127.0.0.1
        ports: ["3306"]
`)

	path := filepath.Join(t.TempDir(), "probe.yaml")
	if err := os.WriteFile(path, doc, 0o644); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}

	fromFile, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse from file failed, errmsg: %s", err)
	}
	fromBytes, err := config.ParseBytes(doc)
	if err != nil {
		t.Fatalf("parse from bytes failed, errmsg: %s", err)
	}

	if !reflect.DeepEqual(fromFile, fromBytes) {
		t.Fatalf("parse paths diverged, file: %+v, bytes: %+v", fromFile, fromBytes)
	}
	if fromBytes.PidFile == "" {
		t.Error("expected pidFile fallback to be applied by ParseBytes")
	}
}

// TestParseBytes_RejectsInvalidDocument is the guard that keeps a malformed rendering from
// reaching disk: periodic sync validates before writing and must see an error here.
func TestParseBytes_RejectsInvalidDocument(t *testing.T) {
	if _, err := config.ParseBytes([]byte("name: probe\n  bad-indent: true\n")); err == nil {
		t.Fatal("expected malformed yaml to be rejected")
	}
	// An empty duration string is the specific shape a zero-valued Duration would render to.
	if _, err := config.ParseBytes([]byte("name: probe\nclient:\n  pingTime: \"\"\n")); err == nil {
		t.Fatal("expected empty duration string to be rejected")
	}
}

// TestParse_FromDefaultsClearsOmittedBlocks ensures Parse starts from
// defaultConfiguration so omitted harvester keys do not retain a previous load.
func TestParse_FromDefaultsClearsOmittedBlocks(t *testing.T) {
	restoreCfg(t)

	dir := t.TempDir()
	withRedis := filepath.Join(dir, "with-redis.yaml")
	withoutRedis := filepath.Join(dir, "without-redis.yaml")

	if err := os.WriteFile(withRedis, []byte(`
name: probe
harvester:
  redis:
    user: u
    password: p
    interval: 10s
    timeout: 1s
    endpoints:
      - ip: 127.0.0.1
        ports: ["6379"]
`), 0o644); err != nil {
		t.Fatalf("write with-redis failed, errmsg: %s", err)
	}
	if err := os.WriteFile(withoutRedis, []byte("name: probe\n"), 0o644); err != nil {
		t.Fatalf("write without-redis failed, errmsg: %s", err)
	}

	if err := config.Load(withRedis); err != nil {
		t.Fatalf("load with-redis failed, errmsg: %s", err)
	}
	if config.Cfg.Harvester.Redis == nil {
		t.Fatal("expected redis block after first load")
	}

	next, err := config.Parse(withoutRedis)
	if err != nil {
		t.Fatalf("parse without-redis failed, errmsg: %s", err)
	}
	if next.Harvester.Redis != nil {
		t.Fatal("expected redis block cleared when omitted from file")
	}
}

// TestLoad_EmptyPidFileFallback ensures that an explicitly empty pidFile in the
// config is normalized to the default at load time, so the running process
// never operates with an empty pid-file path.
func TestLoad_EmptyPidFileFallback(t *testing.T) {
	restoreCfg(t)

	dir := t.TempDir()
	path := filepath.Join(dir, "probe.yaml")
	if err := os.WriteFile(path, []byte("name: probe\npidFile: \"\"\n"), 0o644); err != nil {
		t.Fatalf("write temp config failed, errmsg: %s", err)
	}

	if err := config.Load(path); err != nil {
		t.Fatalf("load config failed, errmsg: %s", err)
	}

	const wantPidFile = "./pids/probe.pid"
	if config.Cfg.PidFile != wantPidFile {
		t.Fatalf("PidFile = %q, want %q", config.Cfg.PidFile, wantPidFile)
	}
}

func TestRetainIdentity(t *testing.T) {
	old := config.Configuration{
		PidFile: "./pids/old.pid",
		Log: config.LogConfig{
			Path:  "./logs/old.log",
			Level: "info",
		},
		ServiceID: "old",
	}
	next := config.Configuration{
		PidFile: "./pids/new.pid",
		Log: config.LogConfig{
			Path:  "./logs/new.log",
			Level: "debug",
		},
		ServiceID: "new",
	}
	got := config.RetainIdentity(old, next)
	if got.PidFile != old.PidFile {
		t.Fatalf("PidFile = %q, want %q", got.PidFile, old.PidFile)
	}
	if got.Log != old.Log {
		t.Fatalf("Log = %+v, want %+v", got.Log, old.Log)
	}
	if got.ServiceID != "new" {
		t.Fatalf("ServiceID = %q, want new", got.ServiceID)
	}
}

func TestParse_DoesNotMutateCfg(t *testing.T) {
	restoreCfg(t)

	dir := t.TempDir()
	keep := filepath.Join(dir, "keep.yaml")
	other := filepath.Join(dir, "other.yaml")
	if err := os.WriteFile(keep, []byte("name: probe\nserviceID: keep\n"), 0o644); err != nil {
		t.Fatalf("write keep failed, errmsg: %s", err)
	}
	if err := os.WriteFile(other, []byte("name: probe\nserviceID: other\n"), 0o644); err != nil {
		t.Fatalf("write other failed, errmsg: %s", err)
	}
	if err := config.Load(keep); err != nil {
		t.Fatalf("load keep failed, errmsg: %s", err)
	}
	before := config.Cfg

	got, err := config.Parse(other)
	if err != nil {
		t.Fatalf("parse other failed, errmsg: %s", err)
	}
	if got.ServiceID != "other" {
		t.Fatalf("parsed ServiceID: %q, want other", got.ServiceID)
	}
	if !reflect.DeepEqual(before, config.Cfg) {
		t.Fatal("Parse mutated package-level Cfg")
	}
}

func TestParse_DoesNotTouchGlobalViper(t *testing.T) {
	restoreCfg(t)
	viper.Reset()
	t.Cleanup(viper.Reset)

	dir := t.TempDir()
	path := filepath.Join(dir, "probe.yaml")
	if err := os.WriteFile(path, []byte("name: probe\nserviceID: parsed\n"), 0o644); err != nil {
		t.Fatalf("write failed, errmsg: %s", err)
	}
	if _, err := config.Parse(path); err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if got := viper.GetString("name"); got != "" {
		t.Fatalf("global viper name: %q, want empty", got)
	}
}

func TestParse_EmptyPidFileFallback(t *testing.T) {
	restoreCfg(t)

	dir := t.TempDir()
	path := filepath.Join(dir, "probe.yaml")
	if err := os.WriteFile(path, []byte("name: probe\npidFile: \"\"\n"), 0o644); err != nil {
		t.Fatalf("write failed, errmsg: %s", err)
	}
	got, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	const wantPidFile = "./pids/probe.pid"
	if got.PidFile != wantPidFile {
		t.Fatalf("PidFile = %q, want %q", got.PidFile, wantPidFile)
	}
}

func TestLoad_FailedParseDoesNotMutateCfg(t *testing.T) {
	restoreCfg(t)

	dir := t.TempDir()
	ok := filepath.Join(dir, "ok.yaml")
	if err := os.WriteFile(ok, []byte("name: probe\nserviceID: keep\n"), 0o644); err != nil {
		t.Fatalf("write ok failed, errmsg: %s", err)
	}
	if err := config.Load(ok); err != nil {
		t.Fatalf("load ok failed, errmsg: %s", err)
	}

	err := config.Load(filepath.Join(dir, "missing.yaml"))
	if err == nil {
		t.Fatal("expected load error for missing file")
	}
	if config.Cfg.ServiceID != "keep" {
		t.Fatalf("ServiceID = %q, want keep after failed load", config.Cfg.ServiceID)
	}
}
