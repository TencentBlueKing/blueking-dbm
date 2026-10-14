package common

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestSmokeMongoShellLocal 用临时安装目录里的假客户端做本地冒烟。
// 优先使用 mongosh；没有 mongosh 时回退到 mongo。
func TestSmokeMongoShellLocal(t *testing.T) {
	cases := []struct {
		name        string
		withMongo   bool
		withMongosh bool
		wantShell   string
	}{
		{
			name:        "mongosh is preferred when both exist",
			withMongo:   true,
			withMongosh: true,
			wantShell:   "mongosh",
		},
		{
			name:      "mongo is used when mongosh is absent",
			withMongo: true,
			wantShell: "mongo",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			binDir := t.TempDir()
			if c.withMongo {
				writeSmokeShell(t, binDir, "mongo", "mongo")
			}
			if c.withMongosh {
				writeSmokeShell(t, binDir, "mongosh", "mongosh")
			}

			got, err := ResolveMongoShellBin(binDir)
			if err != nil {
				t.Fatalf("ResolveMongoShellBin: %v", err)
			}
			if filepath.Base(got) != c.wantShell {
				t.Fatalf("shell=%s, want %s", got, c.wantShell)
			}
			if _, err := os.Stat(got); err != nil {
				t.Fatalf("selected shell missing: %s: %v", got, err)
			}
			out, err := exec.Command(got, "--quiet", "--eval", "db.version()").CombinedOutput()
			if err != nil {
				t.Fatalf("run %s: %v output=%s", got, err, out)
			}
			if strings.TrimSpace(string(out)) != c.wantShell {
				t.Fatalf("shell identified as %q, want %q", strings.TrimSpace(string(out)), c.wantShell)
			}
		})
	}
}

func writeSmokeShell(t *testing.T, binDir, name, ident string) {
	t.Helper()
	body := "#!/bin/sh\necho " + ident + "\n"
	writeSmokeExecutable(t, filepath.Join(binDir, "mongodb", "bin", name), body)
}

func writeSmokeExecutable(t *testing.T, path, body string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(path, []byte(body), 0o755); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}
