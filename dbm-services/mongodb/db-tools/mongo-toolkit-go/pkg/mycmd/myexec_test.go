// create a test file
package mycmd

import (
	"bytes"
	"os"
	"testing"
	"time"
)

func TestMyExec(t *testing.T) {
	os.Remove("test.zst")
	tmpContent := "hello" + time.Now().Format("2006-01-02 15:04:05")
	exec, err := NewMyExec(NewCmdBuilder().Append("echo", "-n", tmpContent), 10*time.Second, nil, os.Stdout, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}

	// cancel() if timeout > 0
	defer exec.CancelFunc()

	exec2, err := NewMyExec(NewCmdBuilder().Append("zstd", "-", "-o", "test.zst"), 0, os.DevNull, os.Stderr, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	// connect stdout of exec to stdin of exec2
	out1, err := exec.ExecHandle.StdoutPipe()
	if err != nil {
		t.Errorf("StdoutPipe failed: %v", err)
	}
	exec2.SetStdin(out1)

	for _, e := range []*MyExec{exec, exec2} {
		err := e.Start()
		if err != nil {
			t.Errorf("Start failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Start success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	for _, e := range []*MyExec{exec, exec2} {
		err := e.Wait()
		if err != nil {
			t.Errorf("Wait failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Wait success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	if _, err := os.Stat("test.zst"); err == nil {
		t.Logf("test.zst found")
	} else {
		t.Errorf("test.zst not found: %v", err)
	}

	outBuffer := bytes.NewBuffer(nil)
	exec3, err := NewMyExec(NewCmdBuilder().Append("zstdcat", "test.zst"), 0, outBuffer, os.Stdout, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	err = exec3.Start()
	if err != nil {
		t.Errorf("Start failed: %v", err)
		return
	}
	err = exec3.Wait()
	if err != nil {
		t.Errorf("Wait failed: %v", err)
		return
	}

	out := outBuffer.String()
	if out != tmpContent {
		t.Errorf("zstdcat output: %s, expected: %s", out, tmpContent)
	} else {
		t.Logf("zstdcat output: %s, expected: %s", out, tmpContent)
	}
}

func TestDump(t *testing.T) {
	tmpDir := os.TempDir()
	archivePath := tmpDir + "/dump.archive.zst"
	dumpLogPath := tmpDir + "/dump.log"
	os.Remove(archivePath)
	os.Remove(dumpLogPath)

	exec, err := NewMyExec(NewCmdBuilder().Append(
		"/data/home/cycker/my/mongotools/mongodump.100.7",
		"--host", "127.0.0.1",
		"--port", "27003",
		"-uroot",
		"-proot",
		"--authenticationDatabase", "admin",
		"--archive",
	), 7*24*time.Hour, nil, dumpLogPath, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	defer exec.CancelFunc()

	exec2, err := NewMyExec(NewCmdBuilder().Append("zstd", "-", "-o", archivePath),
		7*24*time.Hour, os.DevNull, os.Stderr, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	defer exec2.CancelFunc()

	cmd1Output, err := exec.ExecHandle.StdoutPipe()
	if err != nil {
		t.Errorf("StdoutPipe failed: %v", err)
	}
	exec2.SetStdin(cmd1Output)

	for _, e := range []*MyExec{exec, exec2} {
		err := e.Start()
		if err != nil {
			t.Errorf("Start failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Start success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	for _, e := range []*MyExec{exec, exec2} {
		err := e.Wait()
		if err != nil {
			t.Errorf("Wait failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Wait success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	if _, err := os.Stat(archivePath); err == nil {
		t.Logf("dump.zst found, %s", archivePath)
	} else {
		t.Errorf("%s not found: %v", archivePath, err)
	}
}

func TestRestore(t *testing.T) {
	tmpDir := os.TempDir()
	archivePath := tmpDir + "/dump.archive.zst"
	zstdErrPath := tmpDir + "/zstd.err"
	restoreLogPath := tmpDir + "/restore.log"
	os.Remove(restoreLogPath)

	exec1, err := NewMyExec(NewCmdBuilder().Append(
		"zstd",
		"-dcf", archivePath,
	), 80*24*time.Hour, nil, zstdErrPath, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	defer exec1.CancelFunc()

	exec2, err := NewMyExec(NewCmdBuilder().Append(
		"/data/home/cycker/my/mongotools/mongorestore.100.7",
		"--host", "127.0.0.1",
		"--port", "27003",
		"-uroot",
		"-proot",
		"--authenticationDatabase", "admin",
		"--archive"), 80*24*time.Hour, nil, restoreLogPath, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	defer exec2.CancelFunc()

	out1, err := exec1.ExecHandle.StdoutPipe()
	if err != nil {
		t.Errorf("StdoutPipe failed: %v", err)
	}

	exec2.SetStdin(out1)

	for _, e := range []*MyExec{exec1, exec2} {
		err := e.Start()
		if err != nil {
			t.Errorf("Start failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Start success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	for _, e := range []*MyExec{exec1, exec2} {
		err := e.Wait()
		if err != nil {
			t.Errorf("Wait failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err)
		} else {
			t.Logf("Wait success %s", e.CmdBuilder.GetCmdLine("", true))
		}
	}

	if _, err := os.Stat(restoreLogPath); err == nil {
		t.Logf("restore.log found, %s", restoreLogPath)
	} else {
		t.Errorf("%s not found: %v", restoreLogPath, err)
	}
}
