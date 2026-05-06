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
	"errors"
	"os"
	"testing"
	"time"
)

func TestStopOptions(t *testing.T) {
	opt := StopOptions{
		PidFile:  "/var/run/test.pid",
		ProcName: "test-process",
		Timeout:  30 * time.Second,
		Force:    true,
	}

	if opt.PidFile != "/var/run/test.pid" {
		t.Fatalf("PidFile = %v, want /var/run/test.pid", opt.PidFile)
	}
	if opt.ProcName != "test-process" {
		t.Fatalf("ProcName = %v, want test-process", opt.ProcName)
	}
	if opt.Timeout != 30*time.Second {
		t.Fatalf("Timeout = %v, want 30s", opt.Timeout)
	}
	if !opt.Force {
		t.Fatal("Force = false, want true")
	}
}

func TestStopWithPidFile_PidFileNotExist(t *testing.T) {
	opt := StopOptions{
		PidFile:  "/nonexistent/path/test.pid",
		ProcName: "test",
		Timeout:  5 * time.Second,
	}

	err := StopWithPidFile(opt)
	if !errors.Is(err, ErrProcessNotRunning) {
		t.Fatalf("StopWithPidFile() error = %v, want ErrProcessNotRunning", err)
	}
}

func TestStopWithPidFile_InvalidPidFile(t *testing.T) {
	opt := StopOptions{
		PidFile:  "",
		ProcName: "test",
		Timeout:  5 * time.Second,
	}

	err := StopWithPidFile(opt)
	if !errors.Is(err, ErrProcessNotRunning) {
		t.Fatalf("StopWithPidFile() error = %v, want ErrProcessNotRunning", err)
	}
}

func TestStopWithPidFile_ProcessNotRunning(t *testing.T) {
	// Create a temp pid file with a non-existent pid
	tmpFile, err := os.CreateTemp("", "test_stop_*.pid")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write a very high PID that likely doesn't exist
	_, err = tmpFile.WriteString("999999999")
	if err != nil {
		t.Fatalf("Failed to write to temp file: %v", err)
	}
	tmpFile.Close()

	opt := StopOptions{
		PidFile:  tmpFile.Name(),
		ProcName: "nonexistent-process",
		Timeout:  5 * time.Second,
	}

	err = StopWithPidFile(opt)
	if !errors.Is(err, ErrProcessNotRunning) {
		t.Fatalf("StopWithPidFile() error = %v, want ErrProcessNotRunning", err)
	}
}

func TestErrProcessNotRunning(t *testing.T) {
	if ErrProcessNotRunning == nil {
		t.Fatal("ErrProcessNotRunning should not be nil")
	}
}
