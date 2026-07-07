//go:build unix

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
	"fmt"
	"os"
	"syscall"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/spf13/cobra"
)

// signalStop requests graceful termination of proc (SIGTERM on Unix).
// The pidFile argument is unused on Unix; it exists for signature parity with
// the Windows implementation which derives a named event from the pid file.
func signalStop(proc *os.Process, _ string, _ int32, _ string) error {
	return proc.Signal(syscall.SIGTERM)
}

// forceKill forcibly terminates proc (SIGKILL on Unix). The pid file is removed
// by the shared StopWithPidFile force branch, so it is not touched here.
func forceKill(proc *os.Process, _ string) error {
	return proc.Signal(syscall.SIGKILL)
}

// guardStopChild nudges the guard's child toward graceful shutdown. On Unix the
// child runs in its own session (Setsid) and does not receive the signal sent to
// the guard, so the guard forwards SIGTERM to it explicitly.
func guardStopChild(child *os.Process) {
	_ = child.Signal(syscall.SIGTERM)
}

// forwardReloadToChild forwards a reload request to the guard's child. On Unix
// this maps to SIGHUP, preserving the existing guard behavior of relaying the
// reload signal to the worker.
func forwardReloadToChild(child *os.Process) {
	_ = child.Signal(syscall.SIGHUP)
}

// reloadProcess performs the platform reload action against proc and prints the
// result. On Unix this sends SIGHUP; the output text is kept byte-identical to
// the previous inline implementation to avoid regressions.
func reloadProcess(cmd *cobra.Command, proc *os.Process, _ string, procName string, pid int32) error {
	if err := proc.Signal(os.Signal(syscall.SIGHUP)); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to send SIGHUP to %s (pid=%d): %s", procName, pid, err)
	}
	fmt.Fprintf(cmd.OutOrStdout(), "sent SIGHUP to %s (pid=%d) for reload\n", procName, pid)
	return nil
}
