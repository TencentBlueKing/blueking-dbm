package atommongodb

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReplaceFileAtomicallyReplacesExistingFile(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo-toolkit-go_Linux.new")
	dst := filepath.Join(dir, "mongo-toolkit-go_Linux")

	if err := os.WriteFile(src, []byte("new toolkit"), 0755); err != nil {
		t.Fatalf("write src failed: %v", err)
	}
	if err := os.WriteFile(dst, []byte("old toolkit"), 0755); err != nil {
		t.Fatalf("write dst failed: %v", err)
	}

	if err := replaceFileAtomically(src, dst); err != nil {
		t.Fatalf("replaceFileAtomically failed: %v", err)
	}

	got, err := os.ReadFile(dst)
	if err != nil {
		t.Fatalf("read dst failed: %v", err)
	}
	if string(got) != "new toolkit" {
		t.Fatalf("dst content mismatch, got %q", string(got))
	}
}

func TestReplaceFileAtomicallyKeepsExecutablePermission(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo-toolkit-go_Linux.new")
	dst := filepath.Join(dir, "mongo-toolkit-go_Linux")

	if err := os.WriteFile(src, []byte("new toolkit"), 0755); err != nil {
		t.Fatalf("write src failed: %v", err)
	}

	if err := replaceFileAtomically(src, dst); err != nil {
		t.Fatalf("replaceFileAtomically failed: %v", err)
	}

	info, err := os.Stat(dst)
	if err != nil {
		t.Fatalf("stat dst failed: %v", err)
	}
	if info.Mode().Perm()&0111 == 0 {
		t.Fatalf("dst must keep executable permission, mode=%v", info.Mode().Perm())
	}
}

func TestReplaceFileAtomicallyCleansTempFileOnRenameError(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo-toolkit-go_Linux.new")
	dst := filepath.Join(dir, "mongo-toolkit-go_Linux")

	if err := os.WriteFile(src, []byte("new toolkit"), 0755); err != nil {
		t.Fatalf("write src failed: %v", err)
	}
	if err := os.Mkdir(dst, 0755); err != nil {
		t.Fatalf("mkdir dst failed: %v", err)
	}

	if err := replaceFileAtomically(src, dst); err == nil {
		t.Fatalf("replaceFileAtomically should fail when dst is a directory")
	}
	assertNoReplaceTempFiles(t, dir)
	if info, err := os.Stat(dst); err != nil {
		t.Fatalf("dst directory should remain, err=%v", err)
	} else if !info.IsDir() {
		t.Fatalf("dst should remain a directory")
	}
}

func TestUntarMediaUsesAtomicReplaceForSingleFile(t *testing.T) {
	dir := t.TempDir()
	prevFile := filepath.Join(dir, "prev-mongo-toolkit-go_Linux")
	newFile := filepath.Join(dir, "mongo-toolkit-go_Linux")
	dstDir := filepath.Join(dir, "dst")
	dstFile := filepath.Join(dstDir, "mongo-toolkit-go_Linux")

	if err := os.Mkdir(dstDir, 0755); err != nil {
		t.Fatalf("mkdir dst failed: %v", err)
	}
	if err := os.WriteFile(newFile, []byte("new toolkit"), 0755); err != nil {
		t.Fatalf("write newFile failed: %v", err)
	}
	if err := os.WriteFile(dstFile, []byte("old toolkit"), 0755); err != nil {
		t.Fatalf("write dstFile failed: %v", err)
	}

	skipped, err := untarMedia(prevFile, newFile, dstDir)
	if err != nil {
		t.Fatalf("untarMedia failed: %v", err)
	}
	if skipped {
		t.Fatalf("untarMedia should not skip when prev file is missing")
	}

	got, err := os.ReadFile(dstFile)
	if err != nil {
		t.Fatalf("read dstFile failed: %v", err)
	}
	if string(got) != "new toolkit" {
		t.Fatalf("dstFile content mismatch, got %q", string(got))
	}
	assertNoReplaceTempFiles(t, dstDir)
}

func assertNoReplaceTempFiles(t *testing.T, dir string) {
	t.Helper()

	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read dir failed: %v", err)
	}
	for _, entry := range entries {
		if strings.Contains(entry.Name(), ".tmp.") {
			t.Fatalf("temp file should be cleaned up, found %s", entry.Name())
		}
	}
}
