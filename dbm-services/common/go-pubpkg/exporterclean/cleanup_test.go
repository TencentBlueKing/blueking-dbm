package exporterclean

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNormalizeExporterNames(t *testing.T) {
	t.Run("fallback to default list", func(t *testing.T) {
		defaults := []string{"dbm_redis_exporter", "dbm_predixy_exporter"}
		names, err := NormalizeExporterNames("", nil, defaults)
		if err != nil {
			t.Fatalf("NormalizeExporterNames returned error: %v", err)
		}
		if len(names) != 2 {
			t.Fatalf("expected 2 names, got %d", len(names))
		}
	})

	t.Run("deduplicate and trim", func(t *testing.T) {
		names, err := NormalizeExporterNames(
			"",
			[]string{" dbm_redis_exporter ", "dbm_redis_exporter", "dbm_twemproxy_exporter"},
			nil,
		)
		if err != nil {
			t.Fatalf("NormalizeExporterNames returned error: %v", err)
		}
		if len(names) != 2 {
			t.Fatalf("expected 2 names after dedup, got %d", len(names))
		}
	})

	t.Run("invalid name", func(t *testing.T) {
		_, err := NormalizeExporterNames("", []string{"redis_exporter"}, nil)
		if err == nil {
			t.Fatalf("expected invalid exporter name error")
		}
	})
}

func TestRemoveExporterFromProcJSON(t *testing.T) {
	proc := []byte(`{
  "plugins": [
    {"procName": "dbm_redis_exporter", "cmdline": "a"},
    {"procName": "dbm_twemproxy_exporter", "cmdline": "b"},
    {"procName": "other_proc", "cmdline": "c"}
  ],
  "nested": {
    "item1": {"procName": "dbm_predixy_exporter"},
    "item2": {"procName": "keep_me"}
  }
}`)

	filtered, changed, err := RemoveExporterFromProcJSON(
		proc,
		[]string{"dbm_redis_exporter", "dbm_predixy_exporter", "dbm_twemproxy_exporter"},
	)
	if err != nil {
		t.Fatalf("RemoveExporterFromProcJSON returned error: %v", err)
	}
	if !changed {
		t.Fatalf("expected changed=true")
	}
	text := string(filtered)
	if ContainsAnyExporterName(text, []string{"dbm_redis_exporter", "dbm_predixy_exporter", "dbm_twemproxy_exporter"}) {
		t.Fatalf("exporter entries should be removed from proc json")
	}
	if !ContainsAnyExporterName(text, []string{"other_proc", "keep_me"}) {
		t.Fatalf("non-exporter entries should be kept")
	}
}

func TestEnsurePathUnderBaseDir(t *testing.T) {
	baseDir := t.TempDir()
	inside := filepath.Join(baseDir, "agent", "etc", ".proc")
	if err := os.MkdirAll(filepath.Dir(inside), 0755); err != nil {
		t.Fatalf("mkdir failed: %v", err)
	}
	if err := EnsurePathUnderBaseDir(baseDir, inside); err != nil {
		t.Fatalf("inside path should be allowed: %v", err)
	}

	outside := "/tmp/not-under-base"
	if err := EnsurePathUnderBaseDir(baseDir, outside); err == nil {
		t.Fatalf("outside path should be rejected")
	}
}

func TestCleanStaleProcFile(t *testing.T) {
	baseDir := t.TempDir()
	setupKeep := filepath.Join(baseDir, "external_plugins", "sub_keep", "dbm_redis_exporter")
	if err := os.MkdirAll(setupKeep, 0755); err != nil {
		t.Fatalf("mkdir setupKeep failed: %v", err)
	}
	procPath := filepath.Join(baseDir, "agent", "etc", ".proc")
	if err := os.MkdirAll(filepath.Dir(procPath), 0755); err != nil {
		t.Fatalf("mkdir proc dir failed: %v", err)
	}
	type procItem struct {
		ProcName  string `json:"procName"`
		SetupPath string `json:"setupPath"`
	}
	root := map[string]any{
		"proc": []procItem{
			{ProcName: "dbm_redis_exporter", SetupPath: setupKeep},                                // keep
			{ProcName: "dbm_redis_exporter", SetupPath: filepath.Join(baseDir, "path_not_exist")}, // remove
			{ProcName: "other_proc", SetupPath: filepath.Join(baseDir, "path_not_exist2")},        // keep
		},
		"meta": "preserved",
	}
	raw, _ := json.Marshal(root)
	if err := os.WriteFile(procPath, raw, 0644); err != nil {
		t.Fatalf("write proc failed: %v", err)
	}

	changed, removed, err := CleanStaleProcFile(baseDir, []string{"dbm_redis_exporter"}, false)
	if err != nil {
		t.Fatalf("CleanStaleProcFile returned error: %v", err)
	}
	if !changed {
		t.Fatalf("expected changed=true")
	}
	if len(removed) != 1 || removed[0] != "dbm_redis_exporter" {
		t.Fatalf("unexpected removed list: %#v", removed)
	}
	updated, err := os.ReadFile(procPath)
	if err != nil {
		t.Fatalf("read updated proc failed: %v", err)
	}
	if !ContainsAnyExporterName(string(updated), []string{"dbm_redis_exporter"}) {
		t.Fatalf("one valid dbm_redis_exporter entry should remain")
	}
	if !ContainsAnyExporterName(string(updated), []string{"other_proc"}) {
		t.Fatalf("non-target entry should be preserved")
	}
}

func TestCleanStaleProcFileAndRestart(t *testing.T) {
	baseDir := t.TempDir()
	procPath := filepath.Join(baseDir, "agent", "etc", ".proc")
	if err := os.MkdirAll(filepath.Dir(procPath), 0755); err != nil {
		t.Fatalf("mkdir proc dir failed: %v", err)
	}
	root := map[string]any{
		"proc": []map[string]string{
			{"procName": "dbm_redis_exporter", "setupPath": filepath.Join(baseDir, "path_not_exist")},
		},
	}
	raw, _ := json.Marshal(root)
	if err := os.WriteFile(procPath, raw, 0644); err != nil {
		t.Fatalf("write proc failed: %v", err)
	}
	restartCalled := 0
	restartFn := func() error {
		restartCalled++
		return nil
	}

	changed, _, restarted, err := CleanStaleProcFileAndRestart(baseDir, []string{"dbm_redis_exporter"}, false, restartFn)
	if err != nil {
		t.Fatalf("CleanStaleProcFileAndRestart returned error: %v", err)
	}
	if !changed || !restarted || restartCalled != 1 {
		t.Fatalf("expected changed/restarted/restartCalled=1, got changed=%v restarted=%v called=%d", changed, restarted, restartCalled)
	}

	changed, _, restarted, err = CleanStaleProcFileAndRestart(baseDir, []string{"dbm_redis_exporter"}, false, restartFn)
	if err != nil {
		t.Fatalf("second CleanStaleProcFileAndRestart returned error: %v", err)
	}
	if changed || restarted || restartCalled != 1 {
		t.Fatalf("expected no restart after no changes, got changed=%v restarted=%v called=%d", changed, restarted, restartCalled)
	}
}

func TestPackageLoggerEmitsOperationLogs(t *testing.T) {
	baseDir := t.TempDir()
	targetDir := filepath.Join(baseDir, "external_plugins", "sub_a_service_b", "dbm_redis_exporter")
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		t.Fatalf("mkdir target exporter dir failed: %v", err)
	}

	var buf bytes.Buffer
	originalLogger := packageLogger
	packageLogger = func(format string, args ...any) {
		_, _ = buf.WriteString(strings.TrimSpace(format))
		_, _ = buf.WriteString("\n")
	}
	defer func() {
		packageLogger = originalLogger
	}()

	_, err := RemoveExporterDirectories(baseDir, []string{"dbm_redis_exporter"}, true)
	if err != nil {
		t.Fatalf("RemoveExporterDirectories returned error: %v", err)
	}
	logText := buf.String()
	if !strings.Contains(logText, "matched exporter directory") {
		t.Fatalf("expected match log, got: %s", logText)
	}
	if !strings.Contains(logText, "dry-run skip remove exporter directory") {
		t.Fatalf("expected dry-run skip log, got: %s", logText)
	}
}
