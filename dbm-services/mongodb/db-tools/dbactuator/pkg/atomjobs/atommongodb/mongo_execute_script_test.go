package atommongodb

import (
	"fmt"
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
	resultPath := filepath.Join(tempDir, "result.txt")
	return &ExecScript{
		runtime:            runtime,
		Mongo:              mongoBin,
		execIP:             host,
		execPort:           port,
		ExecuteDir:         tempDir,
		ScriptFilePathList: []string{scriptPath},
		ResultFilePathList: []string{resultPath},
		ConfParams: &ExecScriptConfParams{
			Port:          port,
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

func TestRunScripts_Success(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	fakeMongo := writeFakeMongo(t, tempDir, "#!/usr/bin/env bash\nset -e\nprintf 'js-executed\\n'\n")
	job := newTestExecScript(t, tempDir, fakeMongo)

	if err := job.runScripts(); err != nil {
		t.Fatalf("runScripts failed: %v", err)
	}

	data, err := os.ReadFile(job.ResultFilePathList[0])
	if err != nil {
		t.Fatalf("read result file failed: %v", err)
	}
	if strings.TrimSpace(string(data)) != "js-executed" {
		t.Fatalf("unexpected result file content: %q", string(data))
	}
}

func TestRunScripts_Fail(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	fakeMongo := writeFakeMongo(
		t,
		tempDir,
		"#!/usr/bin/env bash\nset -e\necho 'run js failed' >&2\nexit 2\n",
	)
	job := newTestExecScript(t, tempDir, fakeMongo)

	err := job.runScripts()
	if err == nil {
		t.Fatal("expected runScripts error, got nil")
	}
	if !strings.Contains(err.Error(), "stderr: run js failed") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestCleanupGeneratedScript(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	job := newTestExecScript(t, tempDir, filepath.Join(tempDir, "mongo"))
	script := filepath.Join(tempDir, "create_extra_user_27001_script.js")
	if err := os.WriteFile(script, []byte("secret"), 0o644); err != nil {
		t.Fatalf("write generated script: %v", err)
	}

	if err := job.cleanupGeneratedScript(script); err != nil {
		t.Fatalf("cleanup generated script: %v", err)
	}
	if _, err := os.Stat(script); !os.IsNotExist(err) {
		t.Fatalf("expected generated script removed, stat err=%v", err)
	}
}

func TestCleanupGeneratedScript_PreserveDownloadedScript(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	job := newTestExecScript(t, tempDir, filepath.Join(tempDir, "mongo"))
	job.ConfParams.ScriptFile = true
	script := filepath.Join(tempDir, "create_extra_user_custom.js")
	if err := os.WriteFile(script, []byte("user script"), 0o644); err != nil {
		t.Fatalf("write downloaded script: %v", err)
	}

	if err := job.cleanupGeneratedScript(script); err != nil {
		t.Fatalf("cleanup downloaded script: %v", err)
	}
	if _, err := os.Stat(script); err != nil {
		t.Fatalf("expected downloaded script preserved, stat err=%v", err)
	}
}

// newTestSkipJob 构造一个「上次已成功执行」的任务：完成标记与非空结果文件都已就绪。
func newTestSkipJob(t *testing.T, execDir string, port int, scriptName string) *ExecScript {
	t.Helper()
	job := &ExecScript{
		ExecuteDir:         execDir,
		ScriptFilePathList: []string{filepath.Join(execDir, fmt.Sprintf("%s_%d_script.js", scriptName, port))},
		ResultFilePathList: []string{filepath.Join(execDir, buildScriptResultFileName("", 1, scriptName))},
		ConfParams:         &ExecScriptConfParams{Port: port, RepoUrl: "http://bkrepo.example.com"},
	}
	if err := os.WriteFile(job.ResultFilePathList[0], []byte("done\n"), 0o644); err != nil {
		t.Fatalf("write result file failed: %v", err)
	}
	marker := job.execDoneMarkerPath(1, job.ScriptFilePathList[0])
	if err := os.WriteFile(marker, []byte("done\n"), 0o644); err != nil {
		t.Fatalf("write done marker failed: %v", err)
	}
	return job
}

func TestCanSkipRunScripts_SameTaskDirDifferentPort(t *testing.T) {
	t.Parallel()

	execDir := t.TempDir()
	done := newTestSkipJob(t, execDir, 27001, "create_extra_user")
	if !done.canSkipRunScripts() {
		t.Fatal("expected skip for the same job that already succeeded")
	}

	// 同一单据目录下的另一个实例：结果文件同名，但脚本尚未执行过，必须重跑。
	other := &ExecScript{
		ExecuteDir:         execDir,
		ScriptFilePathList: []string{filepath.Join(execDir, "create_extra_user_27002_script.js")},
		ResultFilePathList: done.ResultFilePathList,
		ConfParams:         &ExecScriptConfParams{Port: 27002, RepoUrl: "http://bkrepo.example.com"},
	}
	if other.canSkipRunScripts() {
		t.Fatal("expected no skip for a different port sharing the same execute dir")
	}
}

func TestCanSkipRunScripts_WithoutRepo(t *testing.T) {
	t.Parallel()

	job := newTestSkipJob(t, t.TempDir(), 27001, "create_extra_user")
	job.ConfParams.RepoUrl = ""
	if job.canSkipRunScripts() {
		t.Fatal("expected no skip when no repo is configured")
	}
}

func TestExecDoneMarkerPath_PerScriptIdx(t *testing.T) {
	t.Parallel()

	execDir := t.TempDir()
	job := &ExecScript{
		ExecuteDir: execDir,
		ScriptFilePathList: []string{
			filepath.Join(execDir, "a.js"),
			filepath.Join(execDir, "b.js"),
		},
		ResultFilePathList: []string{
			filepath.Join(execDir, buildScriptResultFileName("c", 1, "a")),
			filepath.Join(execDir, buildScriptResultFileName("c", 2, "b")),
		},
		ConfParams: &ExecScriptConfParams{Port: 27001, RepoUrl: "http://bkrepo.example.com"},
	}

	m1 := filepath.Base(job.execDoneMarkerPath(1, job.ScriptFilePathList[0]))
	m2 := filepath.Base(job.execDoneMarkerPath(2, job.ScriptFilePathList[1]))
	if m1 != ".script_exec_done_27001_1_a" {
		t.Fatalf("unexpected marker1: %q", m1)
	}
	if m2 != ".script_exec_done_27001_2_b" {
		t.Fatalf("unexpected marker2: %q", m2)
	}

	// 仅脚本 1 完成时，整体不可 skip，但脚本 1 可判定为 done
	if err := os.WriteFile(job.ResultFilePathList[0], []byte("ok\n"), 0o644); err != nil {
		t.Fatalf("write result: %v", err)
	}
	if err := os.WriteFile(job.execDoneMarkerPath(1, job.ScriptFilePathList[0]), []byte("done\n"), 0o644); err != nil {
		t.Fatalf("write marker: %v", err)
	}
	if !job.isOneScriptDone(0) {
		t.Fatal("expected script #1 done")
	}
	if job.isOneScriptDone(1) {
		t.Fatal("expected script #2 not done")
	}
	if job.canSkipRunScripts() {
		t.Fatal("expected no full skip when only script #1 is done")
	}
}

func TestBuildScriptResultFileName(t *testing.T) {
	t.Parallel()

	got := buildScriptResultFileName("billrs1", 1, "ping")
	want := "billrs1_1_ping_result.txt"
	if got != want {
		t.Fatalf("got %q, want %q", got, want)
	}

	got = buildScriptResultFileName("", 2, "insert")
	want = "cluster_2_insert_result.txt"
	if got != want {
		t.Fatalf("empty clusterName: got %q, want %q", got, want)
	}
}
