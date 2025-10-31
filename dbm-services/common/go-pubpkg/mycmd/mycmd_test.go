package mycmd

import (
	"bytes"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestCmd(t *testing.T) {
	var input = []struct {
		cmd      string
		args     []string
		out, err string
	}{
		{"ls", []string{"."}, "mycmd_test.go", ""},
	}
	for _, v := range input {
		cb := NewCmdBuilder().Append(v.cmd)
		for _, vv := range v.args {
			cb.Append(vv)
		}

		o, err := cb.Run2(5 * time.Second)
		t.Logf("cmd: %s", cb.GetCmdLine("", true))
		t.Logf("return %+q", o)
		assert.NoError(t, err)
		assert.Equal(t, true, strings.Contains(o.GetStdout(), v.out))
		assert.Equal(t, "", o.GetStderr())
		assert.Equal(t, 0, o.ExitCode)
		assert.NoError(t, o.Err)
	}
}

func TestCmdRun2(t *testing.T) {
	var input = []struct {
		cmd      string
		args     []string
		out, err string
	}{
		{"ls", []string{"."}, "mycmd_test.go", ""},
	}
	for _, v := range input {
		cb := NewCmdBuilder().Append(v.cmd)
		for _, vv := range v.args {
			cb.Append(vv)
		}

		o, err := cb.Run2(5 * time.Second)
		assert.NoError(t, err)
		assert.Equal(t, true, strings.Contains(o.Stdout.(*bytes.Buffer).String(), v.out))
		assert.Equal(t, "", o.Stderr.(*bytes.Buffer).String())
		assert.Equal(t, 0, o.ExitCode)
		assert.NoError(t, o.Err)
	}
}

func TestCmdRun3(t *testing.T) {
	var input = []struct {
		cmd      string
		args     []string
		out, err string
	}{
		{"ls", []string{"."}, "mycmd_test.go", ""},
	}
	for _, v := range input {
		cb := NewCmdBuilder().Append(v.cmd)
		for _, vv := range v.args {
			cb.Append(vv)
		}

		outFile, err := os.Create("test_out.log")
		if err != nil {
			t.Errorf("CreateFile failed: %v", err)
			return
		}
		errFile, err := os.Create("test_err.log")
		if err != nil {
			t.Errorf("CreateFile failed: %v", err)
			return
		}
		defer errFile.Close()
		defer outFile.Close()
		o, err := cb.Run3(5*time.Second, outFile, errFile)
		t.Logf("return %+q o.GetStdout() %s o.GetStderr() %s", o, o.GetStdout(), o.GetStderr())
		assert.NoError(t, err)
		assert.Equal(t, true, strings.Contains(o.GetStdout(), v.out))
		assert.Equal(t, "", o.GetStderr())
		assert.Equal(t, 0, o.ExitCode)
		assert.NoError(t, o.Err)
		// delete test_out.log and test_err.log
		os.Remove("test_out.log")
		os.Remove("test_err.log")
	}
}

// TestCmdBuilder 使用Bash执行命令
func TestCmdBuilder(t *testing.T) {
	cb := NewCmdBuilder()
	cb.Append("ls")
	cb.Append(".")
	cb.Append("|")
	cb.Append("grep")
	cb.Append("mycmd_test.go")
	code, stdout, stderr, err := cb.RunByBash("", 5*time.Second)
	t.Logf("code: %d, stdout: %s, stderr: %s, err: %v", code, stdout, stderr, err)
	assert.Equal(t, 0, code)
	assert.NoError(t, err)
	assert.Equal(t, true, strings.Contains(stdout, "mycmd_test.go"))
	assert.Equal(t, "", stderr)
}
