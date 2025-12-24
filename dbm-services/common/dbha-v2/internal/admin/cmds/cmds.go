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

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

var (
	ForceStop     bool
	StopTimeout   int
	JsonFormatter bool
)

func StartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StartCmdRunE(cmd, args, config.Cfg.PidFile, process.NameAdmin)
}

func StopCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StopCmdRunE(cmd, args, config.Cfg.PidFile, process.NameAdmin, StopTimeout, ForceStop)
}

func RestartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.RestartCmdRunE(cmd, args, config.Cfg.PidFile, process.NameAdmin, StopTimeout, ForceStop)
}

func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	return process.ReloadCmdRunE(cmd, args, config.Cfg.PidFile, process.NameAdmin, StopTimeout, ForceStop)
}

func HealthCmdRunE(cmd *cobra.Command, _ []string) error {
	baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, process.NameAdmin)

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
