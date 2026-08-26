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
	"bytes"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/spf13/cobra"
)

func TestGetBaseHealthInfo_NoPidFile(t *testing.T) {
	health := GetBaseHealthInfo("/nonexistent/path/test.pid", "test-process")

	if health == nil {
		t.Fatal("GetBaseHealthInfo() returned nil")
	}
	if health.Pid != InvalidPid {
		t.Fatalf("Pid = %v, want %v", health.Pid, InvalidPid)
	}
	if health.Status != StatusStopped {
		t.Fatalf("Status = %v, want %v", health.Status, StatusStopped)
	}
	if health.ErrMsg == "" {
		t.Fatal("ErrMsg should not be empty when pid file doesn't exist")
	}
}

func TestGetBaseHealthInfo_InvalidPid(t *testing.T) {
	// Create temp pid file with invalid content
	tmpFile, err := os.CreateTemp("", "test_health_*.pid")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	_, err = tmpFile.WriteString("invalid")
	if err != nil {
		t.Fatalf("Failed to write to temp file: %v", err)
	}
	tmpFile.Close()

	health := GetBaseHealthInfo(tmpFile.Name(), "test-process")

	if health == nil {
		t.Fatal("GetBaseHealthInfo() returned nil")
	}
	if health.Status != StatusStopped {
		t.Fatalf("Status = %v, want %v", health.Status, StatusStopped)
	}
}

func TestGetBaseHealthInfo_NonExistentProcess(t *testing.T) {
	// Create temp pid file with non-existent pid
	tmpFile, err := os.CreateTemp("", "test_health_*.pid")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	_, err = tmpFile.WriteString("999999999")
	if err != nil {
		t.Fatalf("Failed to write to temp file: %v", err)
	}
	tmpFile.Close()

	health := GetBaseHealthInfo(tmpFile.Name(), "test-process")

	if health == nil {
		t.Fatal("GetBaseHealthInfo() returned nil")
	}
	if health.Pid != 999999999 {
		t.Fatalf("Pid = %v, want 999999999", health.Pid)
	}
	if health.Status != StatusStopped {
		t.Fatalf("Status = %v, want %v", health.Status, StatusStopped)
	}
}

func TestGetBaseHealthInfo_CurrentProcess(t *testing.T) {
	// Create temp pid file with current process pid
	tmpFile, err := os.CreateTemp("", "test_health_*.pid")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())
	tmpFile.Close()

	currentPid := os.Getpid()

	// Get current process name
	procName, err := Name(int32(currentPid))
	if err != nil {
		t.Fatalf("Failed to get process name: %v", err)
	}

	// Write pid as string
	err = os.WriteFile(tmpFile.Name(), []byte(fmt.Sprintf("%d", currentPid)), 0644)
	if err != nil {
		t.Fatalf("Failed to write pid file: %v", err)
	}

	// This test is limited because we can't easily match our own process name
	health := GetBaseHealthInfo(tmpFile.Name(), procName)
	if health == nil {
		t.Fatal("GetBaseHealthInfo() returned nil")
	}
	if health.Pid != int32(currentPid) {
		t.Fatalf("Pid = %v, want %v", health.Pid, currentPid)
	}
}

func TestPrintBaseHealth(t *testing.T) {
	health := &HealthInfo{
		Pid:      1234,
		ProcName: "test-process",
		Status:   StatusRunning,
		ErrMsg:   "",
	}

	var buf bytes.Buffer
	PrintBaseHealth(&buf, health)

	output := buf.String()
	if output == "" {
		t.Fatal("PrintBaseHealth() produced empty output")
	}

	// Check that output contains expected fields
	expectedFields := []string{"Pid:", "ProcName:", "Status:", "ErrMsg:"}
	for _, field := range expectedFields {
		if !bytes.Contains([]byte(output), []byte(field)) {
			t.Fatalf("PrintBaseHealth() output missing field: %s", field)
		}
	}

	t.Logf("PrintBaseHealth output:\n%s", output)
}

func TestPrintBaseHealth_WithError(t *testing.T) {
	health := &HealthInfo{
		Pid:      InvalidPid,
		ProcName: "test-process",
		Status:   StatusStopped,
		ErrMsg:   "process not found",
	}

	var buf bytes.Buffer
	PrintBaseHealth(&buf, health)

	output := buf.String()
	if !bytes.Contains([]byte(output), []byte("process not found")) {
		t.Fatal("PrintBaseHealth() output should contain error message")
	}
}

func TestConstants(t *testing.T) {
	if InvalidPid != -1 {
		t.Fatalf("InvalidPid = %v, want -1", InvalidPid)
	}
	if NameProbe != "probe" {
		t.Fatalf("NameProbe = %v, want probe", NameProbe)
	}
	if NameReceiver != "receiver" {
		t.Fatalf("NameReceiver = %v, want receiver", NameReceiver)
	}
	if NameAnalysis != "analysis" {
		t.Fatalf("NameAnalysis = %v, want analysis", NameAnalysis)
	}
	if NameAdmin != "admin" {
		t.Fatalf("NameAdmin = %v, want admin", NameAdmin)
	}
}

func TestErrorVariables(t *testing.T) {
	if ErrIsDir == nil {
		t.Fatal("ErrIsDir should not be nil")
	}
	if ErrPidFileNotExist == nil {
		t.Fatal("ErrPidFileNotExist should not be nil")
	}
	if ErrInvalidFile == nil {
		t.Fatal("ErrInvalidFile should not be nil")
	}
	if ErrInvalidPid == nil {
		t.Fatal("ErrInvalidPid should not be nil")
	}
	if ErrInvalidProcName == nil {
		t.Fatal("ErrInvalidProcName should not be nil")
	}
}

func TestIsBenignPidFileErr(t *testing.T) {
	if !isBenignPidFileErr(ErrPidFileNotExist) {
		t.Fatal("ErrPidFileNotExist should be benign")
	}
	if !isBenignPidFileErr(ErrInvalidFile) {
		t.Fatal("ErrInvalidFile should be benign")
	}
	// ErrInvalidPid shares InvalidParameter code with ErrInvalidFile in gerrors.Is, so it is benign too.
	if !isBenignPidFileErr(ErrInvalidPid) {
		t.Fatal("ErrInvalidPid should be benign")
	}
	if isBenignPidFileErr(ErrIsDir) {
		t.Fatal("ErrIsDir should not be benign")
	}
}

func TestSkipStartIfAlreadyRunning(t *testing.T) {
	currentPid := os.Getpid()
	procName, err := Name(int32(currentPid))
	if err != nil {
		t.Fatalf("failed to get process name: %v", err)
	}

	tests := []struct {
		name       string
		pidFile    string
		setup      func(t *testing.T) string
		procName   string
		wantSkip   bool
		wantErr    bool
		wantErrIs  error
		wantOutput string
	}{
		{
			name:     "missing pid file",
			pidFile:  "/nonexistent/path/test.pid",
			procName: "test-process",
			wantSkip: false,
		},
		{
			name:     "invalid pid file path",
			pidFile:  "",
			procName: "test-process",
			wantSkip: false,
		},
		{
			name: "stale pid",
			setup: func(t *testing.T) string {
				t.Helper()
				tmpFile, err := os.CreateTemp("", "test_skip_start_*.pid")
				if err != nil {
					t.Fatalf("failed to create temp file: %v", err)
				}
				t.Cleanup(func() { os.Remove(tmpFile.Name()) })
				if _, err := tmpFile.WriteString("999999999"); err != nil {
					t.Fatalf("failed to write temp file: %v", err)
				}
				tmpFile.Close()
				return tmpFile.Name()
			},
			procName: "test-process",
			wantSkip: false,
		},
		{
			name: "invalid pid content",
			setup: func(t *testing.T) string {
				t.Helper()
				tmpFile, err := os.CreateTemp("", "test_skip_start_*.pid")
				if err != nil {
					t.Fatalf("failed to create temp file: %v", err)
				}
				t.Cleanup(func() { os.Remove(tmpFile.Name()) })
				if _, err := tmpFile.WriteString("invalid"); err != nil {
					t.Fatalf("failed to write temp file: %v", err)
				}
				tmpFile.Close()
				return tmpFile.Name()
			},
			procName: "test-process",
			wantSkip: false,
			wantErr:  true,
		},
		{
			name: "already running",
			setup: func(t *testing.T) string {
				t.Helper()
				tmpFile, err := os.CreateTemp("", "test_skip_start_*.pid")
				if err != nil {
					t.Fatalf("failed to create temp file: %v", err)
				}
				t.Cleanup(func() { os.Remove(tmpFile.Name()) })
				tmpFile.Close()
				if err := os.WriteFile(tmpFile.Name(), []byte(fmt.Sprintf("%d", currentPid)), 0644); err != nil {
					t.Fatalf("failed to write pid file: %v", err)
				}
				return tmpFile.Name()
			},
			procName:   procName,
			wantSkip:   true,
			wantOutput: fmt.Sprintf("%s is already running, pid:%d\n", procName, currentPid),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			pidFile := tt.pidFile
			if tt.setup != nil {
				pidFile = tt.setup(t)
			}

			var buf bytes.Buffer
			skip, err := skipStartIfAlreadyRunning(&buf, pidFile, tt.procName, "")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantErrIs != nil && !errors.Is(err, tt.wantErrIs) {
					t.Fatalf("error = %v, want %v", err, tt.wantErrIs)
				}
			} else if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if skip != tt.wantSkip {
				t.Fatalf("skip = %v, want %v", skip, tt.wantSkip)
			}
			if tt.wantOutput != "" && buf.String() != tt.wantOutput {
				t.Fatalf("output = %q, want %q", buf.String(), tt.wantOutput)
			}
		})
	}
}

func TestConfigFlagArgs(t *testing.T) {
	rootCmd := &cobra.Command{Use: "test"}
	rootCmd.PersistentFlags().StringP("config", "c", "", "config file path")

	childCmd := &cobra.Command{Use: "start"}
	rootCmd.AddCommand(childCmd)

	t.Run("empty config", func(t *testing.T) {
		args, err := configFlagArgs(childCmd)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(args) != 0 {
			t.Fatalf("args = %v, want empty", args)
		}
	})

	t.Run("set config", func(t *testing.T) {
		if err := rootCmd.PersistentFlags().Set("config", "/etc/probe.yaml"); err != nil {
			t.Fatalf("failed to set config flag: %v", err)
		}
		t.Cleanup(func() {
			_ = rootCmd.PersistentFlags().Set("config", "")
		})

		args, err := configFlagArgs(childCmd)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		want := []string{"-c", "/etc/probe.yaml"}
		if len(args) != len(want) {
			t.Fatalf("args = %v, want %v", args, want)
		}
		for i := range want {
			if args[i] != want[i] {
				t.Fatalf("args[%d] = %q, want %q", i, args[i], want[i])
			}
		}
	})
}

func TestReloadCmdRunE_NoPidFileSucceeds(t *testing.T) {
	cmd := &cobra.Command{}
	var buf bytes.Buffer
	cmd.SetOut(&buf)
	pidFile := filepath.Join(t.TempDir(), "missing.pid")
	if err := ReloadCmdRunE(cmd, nil, pidFile, "probe", 0, false); err != nil {
		t.Fatalf("ReloadCmdRunE failed, errmsg: %s", err)
	}
}

func TestReloadIfRunning_NoPidFileErrors(t *testing.T) {
	cmd := &cobra.Command{}
	var buf bytes.Buffer
	cmd.SetOut(&buf)
	pidFile := filepath.Join(t.TempDir(), "missing.pid")
	err := ReloadIfRunning(cmd, pidFile, "probe")
	if !errors.Is(err, ErrProcessNotRunning) {
		t.Fatalf("err: %v, want ErrProcessNotRunning", err)
	}
}
