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

package cmds

import (
	"os"
	"path/filepath"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/config"
)

func TestReloadSignalPidFileMissingConfigUsesCurrentPid(t *testing.T) {
	saved := config.Cfg
	t.Cleanup(func() { config.Cfg = saved })
	config.Cfg.PidFile = filepath.Join(t.TempDir(), "admin.pid")

	missing := filepath.Join(t.TempDir(), "missing.yaml")
	pidFile, err := reloadSignalPidFile(missing)
	if err != nil {
		t.Fatalf("missing config should still return pid file, errmsg: %s", err)
	}
	if pidFile != config.Cfg.PidFile {
		t.Fatalf("pid file: %s, want: %s", pidFile, config.Cfg.PidFile)
	}
}

func TestReloadSignalPidFileRejectsInvalidYAML(t *testing.T) {
	path := filepath.Join(t.TempDir(), "admin.yaml")
	if err := os.WriteFile(path, []byte(":\n- not: yaml: ["), 0o600); err != nil {
		t.Fatalf("write invalid yaml failed, errmsg: %s", err)
	}
	if _, err := reloadSignalPidFile(path); err == nil {
		t.Fatal("invalid yaml should not produce a pid file for signaling")
	}
}

func TestReloadSignalPidFileIgnoresNextPidFile(t *testing.T) {
	saved := config.Cfg
	t.Cleanup(func() { config.Cfg = saved })
	config.Cfg.PidFile = filepath.Join(t.TempDir(), "cli.pid")

	path := filepath.Join(t.TempDir(), "admin.yaml")
	content := `
pidFile: /tmp/next.pid
discovery:
  endpoint: "127.0.0.1:2379"
storage:
  endpoint: "127.0.0.1:3306"
apm:
  listenAddress: "127.0.0.1:19090"
grpc:
  listenAddress: "127.0.0.1:15051"
web:
  listenAddress: "127.0.0.1:18080"
log:
  level: info
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	pidFile, err := reloadSignalPidFile(path)
	if err != nil {
		t.Fatalf("valid config should signal, errmsg: %s", err)
	}
	if pidFile != config.Cfg.PidFile {
		t.Fatalf("pid file: %s, want current Cfg.PidFile", pidFile)
	}
	if pidFile == "/tmp/next.pid" {
		t.Fatal("must not use next.PidFile from yaml")
	}
}
