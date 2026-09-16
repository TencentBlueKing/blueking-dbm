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
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// StopOptions configures StopWithPidFile.
type StopOptions struct {
	PidFile  string
	ProcName string
	Timeout  time.Duration
	Force    bool
}

var (
	ErrProcessNotRunning = gerrors.Newf(gerrors.NotExist, "process is not running")
)

// StopWithPidFile gracefully stops a process identified by pid file
func StopWithPidFile(opt StopOptions) error {
	pid, err := ReadPid(opt.PidFile)
	if err != nil {
		if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
			return ErrProcessNotRunning
		}
		return err
	}

	alive, err := IsAliveWithProcessName(pid, opt.ProcName)
	if err != nil {
		return err
	}

	if !alive {
		return ErrProcessNotRunning
	}

	proc, err := os.FindProcess(int(pid))
	if err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	// Request graceful stop: SIGTERM on Unix; set the named stop event on Windows.
	// On Windows a missing event means the process is not running.
	if err := signalStop(proc, opt.PidFile, pid, opt.ProcName); err != nil {
		if errors.Is(err, ErrProcessNotRunning) {
			return ErrProcessNotRunning
		}
		return gerrors.NewE(gerrors.Failure, err)
	}

	deadline := time.Now().Add(opt.Timeout)

	for {
		time.Sleep(200 * time.Millisecond)

		alive, err := IsAliveWithProcessName(pid, opt.ProcName)
		if err != nil {
			return err
		}

		if !alive {
			return nil
		}

		if time.Now().After(deadline) {
			break
		}
	}

	if !opt.Force {
		return gerrors.Newf(gerrors.Timeout, "stop process timeout after %s, pid=%d", opt.Timeout.String(), pid)
	}

	// Force kill: SIGKILL on Unix; TerminateProcess (os.Process.Kill) on Windows.
	if err := forceKill(proc, opt.PidFile); err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	if opt.PidFile != "" {
		if err := os.Remove(opt.PidFile); err != nil && !os.IsNotExist(err) {
			return gerrors.NewE(gerrors.Failure, err)
		}
	}

	return nil
}
