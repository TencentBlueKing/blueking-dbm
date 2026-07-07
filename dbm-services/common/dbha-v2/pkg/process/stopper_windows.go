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
	"fmt"
	"os"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/spf13/cobra"
)

// signalStop requests graceful termination on Windows by setting the process's
// named stop event (derived from the pid file). The target process waits on this
// event and shuts down gracefully. If the event does not exist, the process is
// treated as not running (mirrors ErrProcessNotRunning on Unix) unless the
// process is still alive, in which case a short retry covers the startup race
// where the pid file was written before the stop event existed.
func signalStop(_ *os.Process, pidFile string, pid int32, procName string) error {
	const retryWindow = 2 * time.Second
	deadline := time.Now().Add(retryWindow)

	for {
		err := setStopEvent(pidFile)
		if err == nil {
			return nil
		}
		if !errors.Is(err, ErrProcessNotRunning) {
			return err
		}

		alive, aerr := IsAliveWithProcessName(pid, procName)
		if aerr != nil {
			return aerr
		}
		if !alive {
			return ErrProcessNotRunning
		}
		if time.Now().After(deadline) {
			return ErrProcessNotRunning
		}
		time.Sleep(100 * time.Millisecond)
	}
}

// forceKill forcibly terminates proc on Windows (TerminateProcess via
// os.Process.Kill). Unlike Unix (where the shared StopWithPidFile branch removes
// the pid file after SIGKILL), the graceful path lets the process remove its own
// pid file; on the force path the process never reached its cleanup, so we remove
// the pid file here to keep symmetry with the Unix force+SIGKILL branch and avoid
// a stale pid file causing the next start to think the process is still running.
func forceKill(proc *os.Process, pidFile string) error {
	err := proc.Kill()
	if pidFile != "" {
		_ = os.Remove(pidFile)
	}
	return err
}

// guardStopChild is a no-op on Windows: the guard and worker share a single
// manual-reset stop event, so setting it once wakes both. The worker shuts down
// on its own; the guard only needs to wait for the child to exit.
func guardStopChild(_ *os.Process) {}

// forwardReloadToChild is a no-op on Windows: the worker listens on the reload
// event directly, so the guard does not forward reload requests to the child.
func forwardReloadToChild(_ *os.Process) {}

// reloadProcess performs the platform reload action against the target on
// Windows by setting its named reload event (derived from the pid file).
func reloadProcess(cmd *cobra.Command, _ *os.Process, pidFile string, procName string, pid int32) error {
	if err := setReloadEvent(pidFile); err != nil {
		if errors.Is(err, ErrProcessNotRunning) {
			fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, stale pid=%d\n", procName, pid)
			return nil
		}
		return gerrors.Newf(gerrors.Failure, "failed to set reload event for %s (pid=%d): %s", procName, pid, err)
	}
	fmt.Fprintf(cmd.OutOrStdout(), "set reload event for %s (pid=%d) for reload\n", procName, pid)
	return nil
}
