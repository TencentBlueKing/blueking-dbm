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

package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spf13/viper"
)

const minimalAnalysisYAML = `name: analysis
version: test
pidFile: ./pids/analysis.pid
discovery:
  endpoint: http://127.0.0.1:2379
  user: root
  password: ""
apm:
  readTimeout: 10s
  writeTimeout: 10s
  listenAddress: 127.0.0.1:8083
workflow:
  lockBusinessWaitTimeout: 5s
  scanTimeout: 60s
  scanInterval: 3s
detector:
  ssh:
    port: 22
    user: root
    password: ""
    timeout: 10s
monitor:
  dataID: 0
  timeout: 10s
storage:
  endpoint: tcp://127.0.0.1:3306
  user: root
  password: ""
  timeout: 10s
log:
  path: ./logs/analysis.log
  level: info
  fileCount: 10
  fileSize: 100
`

func writeTempAnalysisConfig(t *testing.T, checkProbeProcessCmd string) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "analysis.yaml")
	content := minimalAnalysisYAML
	if checkProbeProcessCmd != "" {
		content = strings.Replace(
			minimalAnalysisYAML,
			"detector:\n",
			fmt.Sprintf("detector:\n  checkProbeProcessCmd: %q\n", checkProbeProcessCmd),
			1,
		)
	}

	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write temp analysis.yaml failed, errmsg: %s", err)
	}

	return path
}

func TestLoad_DefaultCheckProbeProcessCmd(t *testing.T) {
	saved := Cfg
	t.Cleanup(func() {
		Cfg = saved
		viper.Reset()
	})

	path := writeTempAnalysisConfig(t, "")
	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if Cfg.Detector.CheckProbeProcessCmd != defaultCheckProbeProcessCmd {
		t.Fatalf("unexpected default, got: %s", Cfg.Detector.CheckProbeProcessCmd)
	}
}

func TestLoad_InvalidCheckProbeProcessCmd(t *testing.T) {
	saved := Cfg
	t.Cleanup(func() {
		Cfg = saved
		viper.Reset()
	})

	path := writeTempAnalysisConfig(t, "cd ~ && rm -rf /")
	if err := Load(path); err == nil {
		t.Fatal("expected Load to fail for invalid checkProbeProcessCmd")
	}
}
