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
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/config"
)

func TestProbeConfigSourceHasNoPackageCfgReads(t *testing.T) {
	data, err := os.ReadFile("probe_config.go")
	if err != nil {
		t.Fatalf("read probe_config.go failed, errmsg: %s", err)
	}
	for i, line := range strings.Split(string(data), "\n") {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "//") {
			continue
		}
		if strings.Contains(line, "Cfg.") && !strings.Contains(line, "metadataCfg.") && !strings.Contains(line, "cfg.") {
			// Match package-level Cfg. reads only (word-boundary style).
			if strings.Contains(line, " Cfg.") || strings.Contains(line, "\tCfg.") || strings.HasPrefix(strings.TrimSpace(line), "Cfg.") {
				t.Fatalf("probe_config.go:%d still reads package-level Cfg: %s", i+1, trimmed)
			}
		}
	}
}

func TestParseAndValidateRejectsEmptyListenAddress(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "admin.yaml")
	content := `
name: admin
pidFile: ./pids/admin.pid
discovery:
  endpoint: "127.0.0.1:2379"
storage:
  endpoint: "127.0.0.1:3306"
apm:
  listenAddress: ""
grpc:
  listenAddress: "127.0.0.1:50051"
web:
  listenAddress: "127.0.0.1:8080"
log:
  level: info
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	cfg, err := config.Parse(path)
	if err != nil {
		t.Fatalf("Parse failed, errmsg: %s", err)
	}
	if err := config.Validate(cfg); err == nil {
		t.Fatal("Validate should reject empty apm.listenAddress")
	} else {
		msg := err.Error()
		if strings.Contains(msg, "password") || strings.Contains(msg, "token") {
			t.Fatalf("Validate error must not leak secrets, errmsg: %s", err)
		}
	}
}

func TestApplySnapshotRoundTrip(t *testing.T) {
	saved := config.Snapshot()
	t.Cleanup(func() { config.Apply(saved) })

	next := saved
	next.Log.Level = "debug"
	config.Apply(next)
	got := config.Snapshot()
	if got.Log.Level != "debug" {
		t.Fatalf("Snapshot level: %s, want debug", got.Log.Level)
	}
}
