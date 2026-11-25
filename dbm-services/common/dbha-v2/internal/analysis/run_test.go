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

package analysis

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/spf13/viper"
)

// writeRunConfig writes an analysis config whose storage and etcd are unreachable,
// so every case must fail at config validation before any network dial.
// workflowExtra and detectorExtra are indented YAML lines placed under those sections.
func writeRunConfig(t *testing.T, workflowExtra, detectorExtra string) {
	t.Helper()

	savedCfg := config.Cfg
	savedPath := ConfigFilePath
	savedLogger := logger.Log()
	t.Cleanup(func() {
		config.Cfg = savedCfg
		ConfigFilePath = savedPath
		logger.SetLogger(savedLogger)
		viper.Reset()
	})

	dir := t.TempDir()
	content := fmt.Sprintf(`name: analysis
pidFile: %s
discovery:
  endpoint: http://127.0.0.1:1
workflow:
  scanInterval: 3s
%sdetector:
  ssh:
    port: 22
%sstorage:
  endpoint: tcp://127.0.0.1:1
  timeout: 1s
log:
  path: %s
  level: info
  fileCount: 1
  fileSize: 10
`, filepath.Join(dir, "analysis.pid"), workflowExtra, detectorExtra, filepath.Join(dir, "analysis.log"))

	ConfigFilePath = filepath.Join(dir, "analysis.yaml")
	if err := os.WriteFile(ConfigFilePath, []byte(content), 0o600); err != nil {
		t.Fatalf("write temp analysis.yaml failed, errmsg: %s", err)
	}
}

func TestRun_RejectsScanWhiteListWithoutAPI(t *testing.T) {
	writeRunConfig(t, "", "")

	err := Run(nil, nil)
	if err == nil {
		t.Fatal("expected Run to fail when scan whitelist is on by default and api is empty")
	}
	if !strings.Contains(err.Error(), "dbhav1ApiBlackWhitelistGet.api") {
		t.Fatalf("unexpected error, errmsg: %s", err)
	}
}

func TestRun_RejectsInvalidCheckProbeProcessCmd(t *testing.T) {
	writeRunConfig(t, "  enableWhiteListForScan: false\n", "  checkProbeProcessCmd: \"cd ~ && rm -rf /\"\n")

	err := Run(nil, nil)
	if err == nil {
		t.Fatal("expected Run to fail for invalid checkProbeProcessCmd")
	}
	if !strings.Contains(err.Error(), "checkProbeProcessCmd") {
		t.Fatalf("unexpected error, errmsg: %s", err)
	}
}

func TestRun_ClampsDbmApiMetadataHashCnt(t *testing.T) {
	writeRunConfig(t, "  dbmApiMetadataHashCnt: 50\n", "")

	if err := Run(nil, nil); err == nil {
		t.Fatal("expected Run to stop at the scan whitelist check")
	}
	if got := config.Cfg.Workflow.DbmApiMetadataHashCnt; got != 200 {
		t.Fatalf("dbmApiMetadataHashCnt: %d, want: 200", got)
	}
}
