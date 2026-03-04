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

package cmds

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/cobra"
)

var (
	ForceStop      bool
	StopTimeout    int
	JsonFormatter  bool
	ConfigFilePath string
)

type ProbeHealthInfo struct {
	*process.HealthInfo
	DbTypes []haprobe.DbType `json:"db_types,omitempty"`
}

func procName() string {
	if n := process.BinaryName(); n != "" {
		return n
	}
	return process.NameProbe
}

func getConfiguredDbTypes() []haprobe.DbType {
	var dbTypes []haprobe.DbType
	if config.Cfg.Harvester.MySql != nil && len(config.Cfg.Harvester.MySql.Endpoints) > 0 {
		dbTypes = append(dbTypes, haprobe.DbTypeMySql)
	}
	if config.Cfg.Harvester.Redis != nil && len(config.Cfg.Harvester.Redis.Endpoints) > 0 {
		dbTypes = append(dbTypes, haprobe.DbTypeRedis)
	}
	return dbTypes
}

func StartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StartCmdRunE(cmd, args, config.Cfg.PidFile, procName())
}

func StopCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop)
}

func RestartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	useDaemonStart, _ := process.WasRunningWithDaemonStart(config.Cfg.PidFile, procName())
	if err := process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop); err != nil {
		return err
	}
	if err := process.WaitForProcessExit(config.Cfg.PidFile, procName(), time.Duration(StopTimeout)*time.Second); err != nil {
		return err
	}
	if useDaemonStart {
		return DaemonStartCmdRunE(cmd, args)
	}
	return StartCmdRunE(cmd, args)
}

func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	return process.ReloadCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop)
}

func DaemonStartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	return process.DaemonStartCmdRunE(cmd, args, config.Cfg.PidFile, procName(), process.DefaultGuardRestartDelay)
}

func HealthCmdRunE(cmd *cobra.Command, _ []string) error {
	if err := config.Load(ConfigFilePath); err != nil {
		baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, procName())
		if !JsonFormatter {
			process.PrintBaseHealth(cmd.OutOrStdout(), baseHealth)
			return nil
		}
		data, _ := json.Marshal(baseHealth)
		fmt.Fprintln(cmd.OutOrStdout(), string(data))
		return nil
	}

	baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, procName())

	probeHealth := &ProbeHealthInfo{
		HealthInfo: baseHealth,
		DbTypes:    getConfiguredDbTypes(),
	}

	if !JsonFormatter {
		process.PrintBaseHealth(cmd.OutOrStdout(), baseHealth)
		if len(probeHealth.DbTypes) > 0 {
			fmt.Fprintln(cmd.OutOrStdout(), "DbTypes:", probeHealth.DbTypes)
		}
		return nil
	}

	data, err := json.Marshal(probeHealth)
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.OutOrStdout(), string(data))
	return nil
}
