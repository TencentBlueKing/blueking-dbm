package kafka

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// chdirTemp switches the test working directory to a temp dir and restores it after the test.
// cst.ProgressFile and cst.ThrottleFile are relative paths, so tests must isolate via cwd.
func chdirTemp(t *testing.T) string {
	t.Helper()
	oldWD, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(oldWD); err != nil {
			t.Errorf("restore working directory: %v", err)
		}
	})
	return dir
}

// TestReadThrottleRate_valid verifies that a valid positive integer is parsed correctly
func TestReadThrottleRate_valid(t *testing.T) {
	f := writeTempFile(t, "100000000\n")
	rate, err := readThrottleRate(f)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rate != 100000000 {
		t.Fatalf("expected 100000000, got %d", rate)
	}
}

// TestReadThrottleRate_emptyFile verifies that an empty file returns an error
func TestReadThrottleRate_emptyFile(t *testing.T) {
	f := writeTempFile(t, "")
	if _, err := readThrottleRate(f); err == nil {
		t.Fatal("expected error for empty file, got nil")
	}
}

// TestReadThrottleRate_nonNumeric verifies that non-numeric content returns an error
func TestReadThrottleRate_nonNumeric(t *testing.T) {
	f := writeTempFile(t, "not-a-number")
	if _, err := readThrottleRate(f); err == nil {
		t.Fatal("expected error for non-numeric content, got nil")
	}
}

// TestReadThrottleRate_negative verifies that a negative value returns an error
func TestReadThrottleRate_negative(t *testing.T) {
	f := writeTempFile(t, "-1")
	if _, err := readThrottleRate(f); err == nil {
		t.Fatal("expected error for negative value, got nil")
	}
}

// TestReadThrottleRate_zero verifies that zero returns an error
func TestReadThrottleRate_zero(t *testing.T) {
	f := writeTempFile(t, "0")
	if _, err := readThrottleRate(f); err == nil {
		t.Fatal("expected error for zero value, got nil")
	}
}

// TestReadThrottleRate_largeValidValue verifies large positive values pass since web tickets have no upper limit
func TestReadThrottleRate_largeValidValue(t *testing.T) {
	f := writeTempFile(t, "10000000000") // 10 GB/s
	if _, err := readThrottleRate(f); err != nil {
		t.Fatalf("expected no error for large positive value, got: %v", err)
	}
}

// TestReadThrottleRate_semicolonInjection verifies that shell metacharacters in throttle_rate.txt are rejected
func TestReadThrottleRate_semicolonInjection(t *testing.T) {
	f := writeTempFile(t, "100;rm -rf /")
	if _, err := readThrottleRate(f); err == nil {
		t.Fatal("expected error for injection payload, got nil")
	}
}

// TestReadThrottleRate_fileNotExist verifies that a missing file returns an error
func TestReadThrottleRate_fileNotExist(t *testing.T) {
	if _, err := readThrottleRate("/nonexistent/path/throttle.txt"); err == nil {
		t.Fatal("expected error for missing file, got nil")
	}
}

// TestWriteAtomically_noBrokenRead verifies that the target file contains correct content and the .tmp file is removed
func TestWriteAtomically_noBrokenRead(t *testing.T) {
	dir := chdirTemp(t)
	path := filepath.Join(dir, "test.json")

	if err := writeAtomically(path, []byte(`{"ok":true}`)); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("file not found after writeAtomically: %v", err)
	}
	if string(data) != `{"ok":true}` {
		t.Errorf("unexpected content: %s", data)
	}

	if _, err := os.Stat(path + ".tmp"); !os.IsNotExist(err) {
		t.Error("expected .tmp file to be gone after rename, but it still exists")
	}
}

// TestWriteProgress_inProgress verifies that in-progress status is written with correct fields and percentage
func TestWriteProgress_inProgress(t *testing.T) {
	dir := chdirTemp(t)

	writeProgress(3, 10, "my-topic", "in_progress")

	data, err := os.ReadFile(filepath.Join(dir, "progress.json"))
	if err != nil {
		t.Fatalf("progress.json not written: %v", err)
	}

	var p struct {
		Current      int     `json:"current"`
		Total        int     `json:"total"`
		Percent      float64 `json:"percent"`
		CurrentTopic string  `json:"current_topic"`
		Status       string  `json:"status"`
	}
	if err := json.Unmarshal(data, &p); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if p.Current != 3 {
		t.Errorf("expected current=3, got %d", p.Current)
	}
	if p.Total != 10 {
		t.Errorf("expected total=10, got %d", p.Total)
	}
	if p.Status != "in_progress" {
		t.Errorf("expected status=in_progress, got %s", p.Status)
	}
	if p.CurrentTopic != "my-topic" {
		t.Errorf("expected current_topic=my-topic, got %s", p.CurrentTopic)
	}
	// percent = 3/10 * 100 = 30.0
	if p.Percent != 30.0 {
		t.Errorf("expected percent=30.0, got %f", p.Percent)
	}
}

// TestWriteProgress_completed verifies that completed status is written with 100% percentage
func TestWriteProgress_completed(t *testing.T) {
	dir := chdirTemp(t)

	writeProgress(5, 5, "", "completed")

	data, _ := os.ReadFile(filepath.Join(dir, "progress.json"))
	var p struct {
		Percent float64 `json:"percent"`
		Status  string  `json:"status"`
	}
	_ = json.Unmarshal(data, &p)

	if p.Percent != 100.0 {
		t.Errorf("expected percent=100.0, got %f", p.Percent)
	}
	if p.Status != "completed" {
		t.Errorf("expected status=completed, got %s", p.Status)
	}
}

// TestWriteProgress_zeroTotal verifies that total=0 does not panic (divide-by-zero guard)
func TestWriteProgress_zeroTotal(t *testing.T) {
	dir := chdirTemp(t)

	writeProgress(0, 0, "", "failed")

	data, _ := os.ReadFile(filepath.Join(dir, "progress.json"))
	var p struct {
		Percent float64 `json:"percent"`
	}
	_ = json.Unmarshal(data, &p)
	if p.Percent != 0.0 {
		t.Errorf("expected percent=0.0 when total=0, got %f", p.Percent)
	}
}

// TestCleanFiles_removesProgressFile verifies that progress.json is removed to prevent stale state being read
func TestCleanFiles_removesProgressFile(t *testing.T) {
	dir := chdirTemp(t)

	progressPath := filepath.Join(dir, "progress.json")
	if err := os.WriteFile(progressPath, []byte(`{"status":"completed"}`), 0644); err != nil {
		t.Fatal(err)
	}
	_ = os.WriteFile(filepath.Join(dir, "throttle_rate.txt"), []byte("100"), 0644)

	cleanFiles()

	if _, err := os.Stat(progressPath); !os.IsNotExist(err) {
		t.Error("expected progress.json to be removed by cleanFiles(), but it still exists")
	}
}

// writeTempFile creates a temp file with the given content and returns its path
func writeTempFile(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "throttle-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := f.WriteString(content); err != nil {
		t.Fatal(err)
	}
	_ = f.Close()
	return f.Name()
}
