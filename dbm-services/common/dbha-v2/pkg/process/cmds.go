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
	"io"
	"os"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/spf13/cobra"
)

// DefaultGuardRestartDelay is the default delay before restarting a crashed child.
const DefaultGuardRestartDelay = 3 * time.Second

// StartCmdRunE handles the start command.
func StartCmdRunE(cmd *cobra.Command, _ []string, pidFile, procName string) error {
	skip, err := skipStartIfAlreadyRunning(cmd.OutOrStdout(), pidFile, procName, "")
	if err != nil || skip {
		return err
	}

	exePath, err := os.Executable()
	if err != nil {
		return err
	}

	childArgs, err := configFlagArgs(cmd)
	if err != nil {
		return err
	}

	_, err = StartDaemon(DaemonOptions{
		Executable: exePath,
		Args:       childArgs,
	})
	return err
}

// DaemonStartCmdRunE handles the daemon-start command. It forks a guard process that
// launches the target via StartDaemon, monitors it, and restarts on abnormal exit.
// The launcher returns immediately; the guard runs in background.
func DaemonStartCmdRunE(cmd *cobra.Command, _ []string, pidFile, procName string, restartDelay time.Duration) error {
	skip, err := skipStartIfAlreadyRunning(cmd.OutOrStdout(), pidFile, procName, "guard mode")
	if err != nil || skip {
		return err
	}

	exePath, err := os.Executable()
	if err != nil {
		return err
	}

	configArgs, err := configFlagArgs(cmd)
	if err != nil {
		return err
	}

	serviceArgs := configArgs
	// Always use "daemon-start" so the forked guard runs RunWithGuard (e.g. when called from restart).
	guardArgs := append([]string{"daemon-start"}, configArgs...)

	if restartDelay <= 0 {
		restartDelay = DefaultGuardRestartDelay
	}

	guardOpt := GuardOptions{
		DaemonOptions: DaemonOptions{
			Executable: exePath,
			Args:       serviceArgs, // child of guard runs the service (e.g. ./probe -c config)
		},
		PidFile:      pidFile,
		ProcName:     procName,
		RestartDelay: restartDelay,
	}

	// If we're the forked guard process, run directly without forking again
	if os.Getenv(EnvGuardProcess) == "1" {
		return RunWithGuard(guardOpt)
	}

	// Fork guard process and return immediately (parent exits)
	_, err = StartDaemon(DaemonOptions{
		Executable: exePath,
		Args:       guardArgs, // guard runs daemon-start (e.g. ./probe daemon-start -c config)
		Env:        []string{EnvGuardProcess + "=1"},
	})
	return err
}

// StopCmdRunE handles the stop command.
func StopCmdRunE(cmd *cobra.Command, _ []string, pidFile, procName string, timeout int, force bool) error {
	pid, err := ReadPid(pidFile)
	if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
		fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", procName)
		return nil
	}
	if err != nil {
		return err
	}

	alive, err := IsAliveWithProcessName(pid, procName)
	if err != nil {
		return err
	}

	if !alive {
		fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", procName)
		return nil
	}

	opt := StopOptions{
		PidFile:  pidFile,
		ProcName: procName,
		Timeout:  time.Duration(timeout) * time.Second,
		Force:    force,
	}

	if err := StopWithPidFile(opt); err != nil {
		if errors.Is(err, ErrProcessNotRunning) {
			fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", procName)
			return nil
		}
		return err
	}

	return nil
}

// RestartCmdRunE handles the restart command.
func RestartCmdRunE(cmd *cobra.Command, args []string, pidFile, procName string, timeout int, force bool) error {
	if err := StopCmdRunE(cmd, args, pidFile, procName, timeout, force); err != nil {
		return err
	}

	// Wait for process to fully terminate
	if err := WaitForProcessExit(pidFile, procName, time.Duration(timeout)*time.Second); err != nil {
		return err
	}

	return StartCmdRunE(cmd, args, pidFile, procName)
}

// WaitForProcessExit waits until the process identified by pid file exits or timeout.
// Used by RestartCmdRunE and by callers that need to wait before re-starting by mode.
func WaitForProcessExit(pidFile, procName string, timeout time.Duration) error {
	return waitForProcessExit(pidFile, procName, timeout)
}

// ReloadCmdRunE handles the reload command.
// Triggers a configuration reload of the target process: SIGHUP on Unix, the
// named reload event on Windows (see reloadProcess).
// When the process is not running it prints a notice and returns nil, matching
// the standalone reload subcommand.
func ReloadCmdRunE(cmd *cobra.Command, _ []string, pidFile, procName string, _ int, _ bool) error {
	return reloadCmdRunE(cmd, pidFile, procName, false)
}

// ReloadIfRunning is like ReloadCmdRunE but returns ErrProcessNotRunning when the
// target is not alive, so callers that requested a reload explicitly cannot succeed
// as a silent no-op.
func ReloadIfRunning(cmd *cobra.Command, pidFile, procName string) error {
	return reloadCmdRunE(cmd, pidFile, procName, true)
}

func reloadCmdRunE(cmd *cobra.Command, pidFile, procName string, requireRunning bool) error {
	pid, err := ReadPid(pidFile)
	if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
		fmt.Fprintf(cmd.OutOrStdout(), "%s is not running (no valid pid file)\n", procName)
		if requireRunning {
			return ErrProcessNotRunning
		}
		return nil
	}
	if err != nil {
		return err
	}

	alive, err := IsAliveWithProcessName(pid, procName)
	if err != nil {
		return err
	}

	if !alive {
		fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, stale pid=%d\n", procName, pid)
		if requireRunning {
			return ErrProcessNotRunning
		}
		return nil
	}

	proc, err := os.FindProcess(int(pid))
	if err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	return reloadProcess(cmd, proc, pidFile, procName, pid)
}

// GetBaseHealthInfo returns basic process health information.
// Services can use this to build their own health response with additional fields.
func GetBaseHealthInfo(pidFile, procName string) *HealthInfo {
	health := &HealthInfo{
		Pid:      InvalidPid,
		ProcName: procName,
		Status:   StatusStopped,
	}

	pid, err := ReadPid(pidFile)
	if err != nil {
		health.ErrMsg = err.Error()
		return health
	}
	health.Pid = pid

	name, err := Name(pid)
	if err != nil {
		health.ErrMsg = err.Error()
	} else {
		health.ProcName = name
	}

	alive, err := IsAliveWithProcessName(pid, procName)
	if err != nil {
		health.ErrMsg = err.Error()
	}
	if alive {
		health.Status = StatusRunning
	}

	return health
}

// PrintBaseHealth prints basic health info to writer.
func PrintBaseHealth(w io.Writer, health *HealthInfo) {
	fmt.Fprintln(w, "Pid:", health.Pid)
	fmt.Fprintln(w, "ProcName:", health.ProcName)
	fmt.Fprintln(w, "Status:", health.Status)
	fmt.Fprintln(w, "ErrMsg:", health.ErrMsg)
}

func waitForProcessExit(pidFile, procName string, timeout time.Duration) error {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	timeoutCh := time.After(timeout)
	for {
		select {
		case <-timeoutCh:
			return gerrors.Newf(gerrors.Failure, "timeout waiting for %s to exit", procName)
		case <-ticker.C:
		}

		pid, err := ReadPid(pidFile)
		if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
			return nil
		}
		if err != nil {
			return err
		}

		alive, aliveErr := IsAliveWithProcessName(pid, procName)
		if aliveErr != nil {
			return aliveErr
		}
		if !alive {
			return nil
		}
	}
}

func isBenignPidFileErr(err error) bool {
	return errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile)
}

func formatAlreadyRunning(procName string, pid int32, modeSuffix string) string {
	if modeSuffix == "" {
		return fmt.Sprintf("%s is already running, pid:%d\n", procName, pid)
	}
	return fmt.Sprintf("%s is already running (%s), pid:%d\n", procName, modeSuffix, pid)
}

// skipStartIfAlreadyRunning checks whether start should be skipped because the process is already running.
// It returns (true, nil) when the process is alive, (false, nil) when start may proceed, and (false, err) on error.
func skipStartIfAlreadyRunning(w io.Writer, pidFile, procName, modeSuffix string) (bool, error) {
	pid, err := ReadPid(pidFile)
	if err != nil {
		if isBenignPidFileErr(err) {
			return false, nil
		}
		return false, err
	}

	alive, err := IsAliveWithProcessName(pid, procName)
	if err != nil {
		return false, err
	}
	if alive {
		fmt.Fprint(w, formatAlreadyRunning(procName, pid, modeSuffix))
		return true, nil
	}
	return false, nil
}

func configFlagArgs(cmd *cobra.Command) ([]string, error) {
	configPath, err := cmd.Root().PersistentFlags().GetString("config")
	if err != nil {
		return nil, err
	}
	if configPath == "" {
		return nil, nil
	}
	return []string{"-c", configPath}, nil
}
