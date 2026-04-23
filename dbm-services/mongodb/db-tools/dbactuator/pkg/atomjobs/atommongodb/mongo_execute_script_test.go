package atommongodb

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
)

func testMongoAddr(t *testing.T) (string, int) {
	t.Helper()
	host := os.Getenv("TEST_MONGO_HOST")
	if host == "" {
		host = "127.0.0.1"
	}
	portStr := os.Getenv("TEST_MONGO_PORT")
	if portStr == "" {
		return host, 27017
	}
	port, err := strconv.Atoi(portStr)
	if err != nil {
		t.Fatalf("invalid TEST_MONGO_PORT=%q: %v", portStr, err)
	}
	return host, port
}

func testMongoAuth() (string, string) {
	user := os.Getenv("TEST_MONGO_USER")
	if user == "" {
		user = "admin"
	}
	pass := os.Getenv("TEST_MONGO_PASS")
	if pass == "" {
		pass = "super-secret-pass"
	}
	return user, pass
}

func newTestExecScript(t *testing.T, tempDir, mongoBin string) *ExecScript {
	t.Helper()
	host, port := testMongoAddr(t)
	user, pass := testMongoAuth()
	runtime, err := jobruntime.NewJobGenericRuntime(
		"ut-uid", "ut-root", "ut-node", "ut-version",
		"{}", consts.PayloadFormatRaw, "mongo_execute_script", "test",
	)
	if err != nil {
		t.Fatalf("new runtime failed: %v", err)
	}
	scriptPath := filepath.Join(tempDir, "test.js")
	if err := os.WriteFile(scriptPath, []byte("print('ok')\n"), 0o644); err != nil {
		t.Fatalf("write js script failed: %v", err)
	}
	return &ExecScript{
		runtime:        runtime,
		Mongo:          mongoBin,
		execIP:         host,
		execPort:       port,
		ScriptFilePath: scriptPath,
		ResultFilePath: filepath.Join(tempDir, "result.txt"),
		ConfParams: &ExecScriptConfParams{
			AdminUsername: user,
			AdminPassword: pass,
		},
	}
}

func writeFakeMongo(t *testing.T, tempDir, scriptContent string) string {
	t.Helper()
	fakeMongo := filepath.Join(tempDir, "mongo")
	if err := os.WriteFile(fakeMongo, []byte(scriptContent), 0o755); err != nil {
		t.Fatalf("write fake mongo failed: %v", err)
	}
	return fakeMongo
}

func TestExecScriptOnly_Success(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	fakeMongo := writeFakeMongo(t, tempDir, "#!/usr/bin/env bash\nset -e\nprintf 'js-executed\\n'\n")
	job := newTestExecScript(t, tempDir, fakeMongo)

	if err := job.execScript(); err != nil {
		t.Fatalf("execScript failed: %v", err)
	}

	data, err := os.ReadFile(job.ResultFilePath)
	if err != nil {
		t.Fatalf("read result file failed: %v", err)
	}
	if strings.TrimSpace(string(data)) != "js-executed" {
		t.Fatalf("unexpected result file content: %q", string(data))
	}
}

func TestExecScriptOnly_Fail(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	fakeMongo := writeFakeMongo(
		t,
		tempDir,
		"#!/usr/bin/env bash\nset -e\necho 'run js failed' >&2\nexit 2\n",
	)
	job := newTestExecScript(t, tempDir, fakeMongo)

	err := job.execScript()
	if err == nil {
		t.Fatal("expected execScript error, got nil")
	}
	if !strings.Contains(err.Error(), "stderr: run js failed") {
		t.Fatalf("unexpected error: %v", err)
	}
}
