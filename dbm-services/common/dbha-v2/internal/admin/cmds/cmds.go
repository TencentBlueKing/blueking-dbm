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

// Package cmds provides cobra command implementations for admin (start, stop, restart, reload, health).
package cmds

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	ForceStop     bool
	StopTimeout   int
	JsonFormatter bool
)

// StartCmdRunE runs the admin process in foreground.
func StartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StartCmdRunE(cmd, args, config.Cfg.PidFile, procName())
}

// StopCmdRunE stops the running admin process.
func StopCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop)
}

// RestartCmdRunE stops then starts the admin process.
func RestartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	useDaemonStart, _ := process.WasRunningWithDaemonStart(config.Cfg.PidFile, procName())
	if err := process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop); err != nil {
		return err
	}
	waitTimeout := time.Duration(StopTimeout) * time.Second
	if err := process.WaitForProcessExit(config.Cfg.PidFile, procName(), waitTimeout); err != nil {
		return err
	}
	if useDaemonStart {
		return DaemonStartCmdRunE(cmd, args)
	}
	return StartCmdRunE(cmd, args)
}

// ReloadCmdRunE sends a reload signal to the running admin process.
func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	pidFile, err := reloadSignalPidFile(configPath)
	if err != nil {
		return err
	}
	return process.ReloadCmdRunE(cmd, args, pidFile, procName(), StopTimeout, ForceStop)
}

// DaemonStartCmdRunE starts the admin process under the process guard.
func DaemonStartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	return process.DaemonStartCmdRunE(cmd, args, config.Cfg.PidFile, procName(), process.DefaultGuardRestartDelay)
}

// HealthCmdRunE prints admin process health information.
func HealthCmdRunE(cmd *cobra.Command, _ []string) error {
	baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, procName())

	if !JsonFormatter {
		process.PrintBaseHealth(cmd.OutOrStdout(), baseHealth)
		// TODO: print admin-specific health info here
		return nil
	}

	// TODO: add admin-specific fields to JSON output
	data, err := json.Marshal(baseHealth)
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.OutOrStdout(), string(data))
	return nil
}

func procName() string {
	if n := process.BinaryName(); n != "" {
		return n
	}
	return process.NameAdmin
}

func reloadSignalPidFile(configPath string) (string, error) {
	next, err := config.Parse(configPath)
	if isConfigFileMissing(err) {
		logger.Warn(
			"admin reload config file missing, using current pid file, config_path: %s, errmsg: %s",
			configPath, err,
		)
		return config.Cfg.PidFile, nil
	}
	if err != nil {
		return "", err
	}
	if err := config.Validate(next); err != nil {
		return "", err
	}
	return config.Cfg.PidFile, nil
}

func isConfigFileMissing(err error) bool {
	if err == nil {
		return false
	}
	var notFound viper.ConfigFileNotFoundError
	if errors.As(err, &notFound) {
		return true
	}
	return errors.Is(err, os.ErrNotExist)
}
