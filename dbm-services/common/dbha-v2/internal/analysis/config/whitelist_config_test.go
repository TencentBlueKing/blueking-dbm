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
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spf13/viper"
)

func writeTempAnalysisConfigWithWorkflowExtra(t *testing.T, workflowExtra string) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "analysis.yaml")
	content := minimalAnalysisYAML
	if workflowExtra != "" {
		content = strings.Replace(
			minimalAnalysisYAML,
			"workflow:\n",
			"workflow:\n"+workflowExtra,
			1,
		)
	}
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write temp analysis.yaml failed, errmsg: %s", err)
	}
	return path
}

func resetCfgForLoadTest(t *testing.T) {
	t.Helper()
	saved := Cfg
	t.Cleanup(func() {
		Cfg = saved
		viper.Reset()
	})
	Cfg = Configuration{
		Workflow: WorkflowConfig{
			EnableWhiteListForSwitch: true,
		},
	}
}

func TestLoad_WhiteListDefaultsWhenUnset(t *testing.T) {
	resetCfgForLoadTest(t)

	path := writeTempAnalysisConfigWithWorkflowExtra(t, "")
	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if !Cfg.Workflow.EnableWhiteListForSwitch {
		t.Fatal("expected EnableWhiteListForSwitch default true when unset")
	}
	if Cfg.Workflow.EnableWhiteListForScan {
		t.Fatal("expected EnableWhiteListForScan default false when unset")
	}
}

func TestLoad_WhiteListDeprecatedKeyIgnored(t *testing.T) {
	resetCfgForLoadTest(t)

	// Old key is unknown config and must not override the ForSwitch default.
	path := writeTempAnalysisConfigWithWorkflowExtra(t, "  enableWhiteList: false\n")
	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if !Cfg.Workflow.EnableWhiteListForSwitch {
		t.Fatal("expected EnableWhiteListForSwitch to stay default true when only deprecated key is present")
	}
}

func TestLoad_WhiteListForScanExplicitTrue(t *testing.T) {
	resetCfgForLoadTest(t)

	path := writeTempAnalysisConfigWithWorkflowExtra(t, "  enableWhiteListForScan: true\n")
	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if !Cfg.Workflow.EnableWhiteListForScan {
		t.Fatal("expected EnableWhiteListForScan=true when explicitly set")
	}
	if !Cfg.Workflow.EnableWhiteListForSwitch {
		t.Fatal("expected EnableWhiteListForSwitch to remain default true")
	}
}
