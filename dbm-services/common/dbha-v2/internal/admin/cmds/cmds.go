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
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

var Flags = process.DefaultCmdFlags()

func cmdConfig() process.CmdConfig {
	return process.CmdConfig{
		PidFile:  config.Cfg.PidFile,
		ProcName: process.NameAdmin,
	}
}

func StartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StartCmdRunE(cmdConfig())(cmd, args)
}

func StopCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StopCmdRunE(cmdConfig(), Flags)(cmd, args)
}

func RestartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.RestartCmdRunE(cmdConfig(), Flags)(cmd, args)
}

func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	return process.ReloadCmdRunE(cmdConfig())(cmd, args)
}

func HealthCmdRunE(cmd *cobra.Command, args []string) error {
	return process.HealthCmdRunE(cmdConfig(), Flags)(cmd, args)
}
