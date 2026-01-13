/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package process

import (
	"os"
	"testing"
	"time"
)

func TestDaemonOptions(t *testing.T) {
	opt := DaemonOptions{
		Executable: "/usr/bin/sleep",
		Args:       []string{"1"},
		Env:        []string{"TEST_VAR=value"},
	}

	if opt.Executable != "/usr/bin/sleep" {
		t.Fatalf("Executable = %v, want /usr/bin/sleep", opt.Executable)
	}
	if len(opt.Args) != 1 || opt.Args[0] != "1" {
		t.Fatalf("Args = %v, want [1]", opt.Args)
	}
	if len(opt.Env) != 1 || opt.Env[0] != "TEST_VAR=value" {
		t.Fatalf("Env = %v, want [TEST_VAR=value]", opt.Env)
	}
}

func TestStartDaemon_EmptyExecutable(t *testing.T) {
	opt := DaemonOptions{
		Executable: "",
	}

	_, err := StartDaemon(opt)
	if err != ErrExecutableEmpty {
		t.Fatalf("StartDaemon() error = %v, want ErrExecutableEmpty", err)
	}
}

func TestStartDaemon_InvalidExecutable(t *testing.T) {
	opt := DaemonOptions{
		Executable: "/nonexistent/path/to/binary",
	}

	_, err := StartDaemon(opt)
	if err == nil {
		t.Fatal("StartDaemon() expected error for invalid executable, got nil")
	}
}

func TestStartDaemon_Success(t *testing.T) {
	// Use sleep command which exists on most Unix systems
	opt := DaemonOptions{
		Executable: "/bin/sleep",
		Args:       []string{"0.1"},
	}

	// Check if /bin/sleep exists, skip if not
	if _, err := os.Stat("/bin/sleep"); os.IsNotExist(err) {
		t.Skip("Skipping test: /bin/sleep not found")
	}

	proc, err := StartDaemon(opt)
	if err != nil {
		t.Fatalf("StartDaemon() error = %v", err)
	}
	if proc == nil {
		t.Fatal("StartDaemon() returned nil process")
	}
	if proc.Pid <= 0 {
		t.Fatalf("StartDaemon() returned invalid pid: %d", proc.Pid)
	}

	t.Logf("Started daemon with pid: %d", proc.Pid)

	// Wait for process to finish
	time.Sleep(200 * time.Millisecond)
}

func TestStartDaemon_WithEnv(t *testing.T) {
	opt := DaemonOptions{
		Executable: "/bin/sleep",
		Args:       []string{"0.1"},
		Env:        []string{"CUSTOM_VAR=test"},
	}

	if _, err := os.Stat("/bin/sleep"); os.IsNotExist(err) {
		t.Skip("Skipping test: /bin/sleep not found")
	}

	proc, err := StartDaemon(opt)
	if err != nil {
		t.Fatalf("StartDaemon() with env error = %v", err)
	}
	if proc == nil {
		t.Fatal("StartDaemon() with env returned nil process")
	}

	t.Logf("Started daemon with env, pid: %d", proc.Pid)
	time.Sleep(200 * time.Millisecond)
}

func TestErrExecutableEmpty(t *testing.T) {
	if ErrExecutableEmpty == nil {
		t.Fatal("ErrExecutableEmpty should not be nil")
	}
}
