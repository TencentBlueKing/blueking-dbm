package common

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDescribeSlowOpThresholdChange(t *testing.T) {
	in := []byte("operationProfiling:\n  slowOpThresholdMs: 200\n  mode: slowOp\n")
	got, err := DescribeSlowOpThresholdChange(in, 200)
	if err != nil {
		t.Fatal(err)
	}
	if got != "" {
		t.Fatalf("unchanged value reported as %q", got)
	}
	got, err = DescribeSlowOpThresholdChange(in, 500)
	if err != nil {
		t.Fatal(err)
	}
	if got != "slowOpThresholdMs 200 -> 500" {
		t.Fatalf("changes = %q", got)
	}
	got, err = DescribeSlowOpThresholdChange([]byte("net:\n  port: 27017\n"), 200)
	if err != nil {
		t.Fatal(err)
	}
	if got != "slowOpThresholdMs unset -> 200" {
		t.Fatalf("missing key changes = %q", got)
	}
	if _, err = DescribeSlowOpThresholdChange(in, 9); err == nil {
		t.Fatal("expected range error")
	}
}

func TestPatchSlowOpThresholdFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "mongo.conf")
	raw := []byte("# listen\nnet:\n  port: 27017\noperationProfiling:\n  # slow\n  slowOpThresholdMs: 200\n  mode: \"slowOp\"\n")
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	backup, err := PatchSlowOpThresholdFile(path, 500)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(backup, path+".bak.") {
		t.Fatalf("backup path = %q", backup)
	}
	backed, err := os.ReadFile(backup)
	if err != nil {
		t.Fatal(err)
	}
	if string(backed) != string(raw) {
		t.Fatalf("backup content changed:\n%s", backed)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	text := string(got)
	for _, keep := range []string{"# listen", "# slow", "mode: \"slowOp\"", "slowOpThresholdMs: 500"} {
		if !strings.Contains(text, keep) {
			t.Fatalf("missing %q in:\n%s", keep, text)
		}
	}
	if strings.Contains(text, "slowOpThresholdMs: 200") {
		t.Fatalf("old value remains:\n%s", text)
	}

	backup, err = PatchSlowOpThresholdFile(path, 500)
	if err != nil {
		t.Fatal(err)
	}
	if backup != "" {
		t.Fatalf("second patch backed up to %s", backup)
	}
}

func TestPatchSlowOpThresholdFileAddsSection(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "mongo.conf")
	raw := []byte("net:\n  port: 27021\n")
	if err := os.WriteFile(path, raw, 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := PatchSlowOpThresholdFile(path, 200); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	text := string(got)
	if !strings.Contains(text, "operationProfiling:\n  slowOpThresholdMs: 200\n") {
		t.Fatalf("section not added:\n%s", text)
	}
	if !strings.Contains(text, "port: 27021") {
		t.Fatalf("other keys lost:\n%s", text)
	}
}
