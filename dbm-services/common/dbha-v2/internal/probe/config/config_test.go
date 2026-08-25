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

	"dbm-services/common/dbha-v2/internal/probe/config"

	"github.com/spf13/viper"
)

func restoreCfg(t *testing.T) {
	t.Helper()
	saved := config.Cfg
	t.Cleanup(func() {
		config.Cfg = saved
	})
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
