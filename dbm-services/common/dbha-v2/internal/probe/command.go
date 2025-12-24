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

package probe

import (
	"dbm-services/common/dbha-v2/internal/probe/cmds"
	"dbm-services/common/dbha-v2/pkg/version"

	"github.com/spf13/cobra"
)

// VersionCmd is used to show the version of this process.
var VersionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print Version Information",
	Run: func(cmd *cobra.Command, args []string) {
		version.Print("DBHA Probe")
	},
}

// HealthCmd is used to show the health information of this process.
var HealthCmd = &cobra.Command{
	Use:   "health",
	Short: "Show the health information of this process",
	RunE:  cmds.HealthCmdRunE,
}

// StartCmd is used to start this process in background (daemon mode).
var StartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start this process.",
	RunE:  cmds.StartCmdRunE,
}

// StopCmd is used to stop this process.
var StopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop this process.",
	RunE:  cmds.StopCmdRunE,
}

// RestartCmd is used to restart this process.
var RestartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart this process.",
	RunE:  cmds.RestartCmdRunE,
}

// ReloadCmd is used to reload this process.
var ReloadCmd = &cobra.Command{
	Use:   "reload",
	Short: "Reload this process.",
	RunE:  cmds.ReloadCmdRunE,
}
