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

package process_test

import (
	"errors"
	"os"
	"testing"

	"dbm-services/common/dbha-v2/pkg/process"
)

const (
	pidFile = "./test.pid"
)

func TestPid(t *testing.T) {
	currentPid := os.Getpid()

	if err := process.SavePid(pidFile); err != nil {
		t.Errorf("failed to save pid, errmsg: %s", err)
	}

	pid, err := process.ReadPid(pidFile)
	if err != nil {
		t.Errorf("failed to read pid, errmsg: %s", err)
	}

	procName, err := process.Name(pid)
	if err != nil {
		t.Errorf("failed to obtain the process name, errmsg: %s", err)
	}

	t.Logf("process name is: %s bound with the pid: %d", procName, pid)

	if pid != int32(currentPid) {
		t.Errorf("the read pid is invalid, errmsg: %s", err)
	}

	exists, err := process.IsAlive(pid)
	if err != nil {
		t.Errorf("failed to check the pid(%d), errmsg: %s", pid, err)
	}

	if exists {
		t.Logf("pid(%d) is alive", pid)
	} else {
		t.Logf("pid(%d) is not alive", pid)
	}

	t.Logf("read pid: %d, current pid: %d", pid, currentPid)

	exists, err = process.IsAliveWithProcessName(pid, procName)
	if err != nil {
		t.Errorf("failed to check the pid(%d) and the proc name: %s, errmsg: %s", pid, procName, err)
	}

	if exists {
		t.Logf("pid(%d) and the proc name: %s, is alive", pid, procName)
	} else {
		t.Logf("pid(%d) and the proc name: %s, is not alive", pid, procName)
	}

	os.Remove(pidFile)
}

func TestIsAliveWithProcessName(t *testing.T) {
	currentPid := int32(os.Getpid())

	procName, err := process.Name(currentPid)
	if err != nil {
		t.Fatalf("failed to get current process name: %s", err)
	}

	_, err = process.IsAliveWithProcessName(0, "test")
	if !errors.Is(err, process.ErrInvalidPid) {
		t.Errorf("expected ErrInvalidPid for pid=0, got: %v", err)
	}

	_, err = process.IsAliveWithProcessName(currentPid, "")
	if !errors.Is(err, process.ErrInvalidProcName) {
		t.Errorf("expected ErrInvalidProcName for empty name, got: %v", err)
	}

	alive, err := process.IsAliveWithProcessName(99999999, "test")
	if err != nil || alive {
		t.Errorf("expected alive=false and no error for non-existent pid, got: alive=%v, err=%v", alive, err)
	}

	alive, err = process.IsAliveWithProcessName(currentPid, procName)
	if err != nil || !alive {
		t.Errorf("expected alive=true and no error for matching process, got: alive=%v, err=%v", alive, err)
	}

	t.Logf("TestIsAliveWithProcessName passed, current pid: %d, proc name: %s", currentPid, procName)
}
