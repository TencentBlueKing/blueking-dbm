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
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"syscall"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/spf13/cobra"
)

// CmdConfig holds the configuration for process commands.
type CmdConfig struct {
	PidFile  string
	ProcName string
}

// CmdFlags holds the flags for process commands.
type CmdFlags struct {
	ForceStop     bool
	StopTimeout   int
	JsonFormatter bool
}

// DefaultCmdFlags returns the default command flags.
func DefaultCmdFlags() *CmdFlags {
	return &CmdFlags{
		ForceStop:     false,
		StopTimeout:   30,
		JsonFormatter: false,
	}
}

// Reset resets all flags to their default values.
// This is useful for testing or when reusing the same CmdFlags instance across multiple command executions.
func (f *CmdFlags) Reset() {
	f.ForceStop = false
	f.StopTimeout = 30
	f.JsonFormatter = false
}

// StartCmdRunE creates a start command handler.
func StartCmdRunE(cfg CmdConfig) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		pid, err := ReadPid(cfg.PidFile)
		if err == nil {
			alive, aliveErr := IsAliveWithProcessName(pid, cfg.ProcName)
			if aliveErr == nil && alive {
				_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is already running, pid:%d\n", cfg.ProcName, pid)
				if printErr != nil {
					return printErr
				}
				return nil
			}
		} else if !errors.Is(err, ErrPidFileNotExist) &&
			!errors.Is(err, ErrInvalidFile) {
			return err
		}

		exePath, err := os.Executable()
		if err != nil {
			return err
		}

		rootCmd := cmd.Root()
		configPath, err := rootCmd.PersistentFlags().GetString("config")
		if err != nil {
			return err
		}

		var childArgs []string
		if configPath != "" {
			childArgs = append(childArgs, "-c", configPath)
		}

		_, err = StartDaemon(DaemonOptions{
			Executable: exePath,
			Args:       childArgs,
		})
		if err != nil {
			return err
		}

		return nil
	}
}

// StopCmdRunE creates a stop command handler.
func StopCmdRunE(cfg CmdConfig, flags *CmdFlags) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		opt := StopOptions{
			PidFile:  cfg.PidFile,
			ProcName: cfg.ProcName,
			Timeout:  time.Duration(flags.StopTimeout) * time.Second,
			Force:    flags.ForceStop,
		}

		pid, err := ReadPid(opt.PidFile)
		if err != nil {
			if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
				_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", cfg.ProcName)
				if printErr != nil {
					return printErr
				}
				return nil
			}
			return err
		}

		alive, err := IsAliveWithProcessName(pid, opt.ProcName)
		if err != nil {
			return err
		}

		if !alive {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", cfg.ProcName)
			if printErr != nil {
				return printErr
			}
			return nil
		}

		if err := StopWithPidFile(opt); err != nil {
			if errors.Is(err, ErrProcessNotRunning) {
				_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", cfg.ProcName)
				if printErr != nil {
					return printErr
				}
				return nil
			}
			return err
		}

		return nil
	}
}

// RestartCmdRunE creates a restart command handler.
func RestartCmdRunE(cfg CmdConfig, flags *CmdFlags) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		stopFn := StopCmdRunE(cfg, flags)
		if err := stopFn(cmd, args); err != nil {
			return err
		}

		time.Sleep(500 * time.Millisecond)

		startFn := StartCmdRunE(cfg)
		return startFn(cmd, args)
	}
}

// ReloadCmdRunE creates a reload command handler.
func ReloadCmdRunE(cfg CmdConfig) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		pid, err := ReadPid(cfg.PidFile)
		if err != nil {
			if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
				_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running (no valid pid file)\n", cfg.ProcName)
				if printErr != nil {
					return printErr
				}
				return nil
			}

			return err
		}

		alive, err := IsAliveWithProcessName(pid, cfg.ProcName)
		if err != nil {
			return err
		}

		if !alive {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, stale pid=%d\n", cfg.ProcName, pid)
			if printErr != nil {
				return printErr
			}
			return nil
		}

		if err := syscall.Kill(int(pid), syscall.SIGHUP); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to reload the process: %s, errmsg: %s", cfg.ProcName, err)
		}

		return nil
	}
}

// HealthCmdRunE creates a health command handler.
func HealthCmdRunE(cfg CmdConfig, flags *CmdFlags) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		healthInfo := obtainHealthInfo(cfg)

		if !flags.JsonFormatter {
			printRawHealth(cmd.OutOrStdout(), healthInfo)
			return nil
		}

		data, err := json.Marshal(healthInfo)
		if err != nil {
			return err
		}

		fmt.Fprintln(cmd.OutOrStdout(), string(data))
		return nil
	}
}

func printRawHealth(w io.Writer, health *HealthInfo) {
	fmt.Fprintln(w, "Pid:", health.Pid)
	fmt.Fprintln(w, "ProcName:", health.ProcName)
	fmt.Fprintln(w, "Status:", health.Status)
	fmt.Fprintln(w, "ErrMsg:", health.ErrMsg)
}

func obtainHealthInfo(cfg CmdConfig) *HealthInfo {
	health := &HealthInfo{
		Pid:      InvalidPid,
		ProcName: cfg.ProcName,
		Status:   StatusStopped,
	}

	pid, err := ReadPid(cfg.PidFile)
	if err != nil {
		health.ErrMsg = err.Error()
		return health
	}
	health.Pid = pid

	procName, err := Name(pid)
	if err != nil {
		health.ErrMsg = err.Error()
	}
	health.ProcName = procName

	alive, err := IsAliveWithProcessName(pid, cfg.ProcName)
	if err != nil {
		health.ErrMsg = err.Error()
	}

	if alive {
		health.Status = StatusRunning
	}

	return health
}
