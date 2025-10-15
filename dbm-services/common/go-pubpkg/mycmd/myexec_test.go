// create a test file
package mycmd

import (
	"bytes"
	"os"
	"testing"
	"time"
)

func TestPipe1(t *testing.T) {
	os.Remove("test.zst")
	tmpContent := "hello" + time.Now().Format("2006-01-02 15:04:05")
	// echo -n hello2025-10-15 10:00:00 | wc -l
	exec, err := NewMyExec(New("echo", tmpContent), 10*time.Second, nil, os.Stdout, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}
	defer exec.CancelFunc()

	outBuffer := bytes.NewBuffer(nil)
	exec2, err := NewMyExec(New("wc", "-l"), 0, outBuffer, os.Stderr, false)
	if err != nil {
		t.Errorf("NewMyExec failed: %v", err)
		return
	}

	// connect exec.Stdout to exec2.Stdin
	err = exec2.ConnectStdin(exec)
	if err != nil {
		t.Errorf("ConnectStdin failed: %v", err)
		return
	}

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

	out := outBuffer.String()
	if out != "1" {
		t.Errorf("wc -l output: %s, expected: %s", out, "1")
	} else {
		t.Logf("wc -l output: %s, expected: %s", out, "1")
	}

}
