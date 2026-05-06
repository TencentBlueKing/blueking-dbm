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
	"fmt"
	"os"
	"testing"
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
