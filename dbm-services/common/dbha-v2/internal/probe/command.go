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

// DaemonStartCmd is used to start this process with a guard that restarts it on abnormal exit.
var DaemonStartCmd = &cobra.Command{
	Use:   "daemon-start",
	Short: "Start this process with guard (auto-restart on crash).",
	RunE:  cmds.DaemonStartCmdRunE,
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

// GenConfigCmd is used to generate probe configuration file from admin server.
var GenConfigCmd = &cobra.Command{
	Use:   "gen-config",
	Short: "Generate probe configuration file from admin server.",
	RunE:  cmds.GenConfigCmdRunE,
}

// EnsureCmd ensures probe is running as guard+worker (for schtasks/crontab).
var EnsureCmd = &cobra.Command{
	Use:   "ensure",
	Short: "Ensure probe is running (chdir InstallRoot, lock, daemon-start if needed).",
	Long: "Intended for Scheduled Task / crontab. Does not register tasks. " +
		"Lock contention always exits 0, regardless of --from-cron.",
	RunE: cmds.EnsureCmdRunE,
}

// EnsureKeepaliveCmd ensures the keepalive ping process is running.
var EnsureKeepaliveCmd = &cobra.Command{
	Use:   "ensure-keepalive",
	Short: "Ensure keepalive ping process is running (for schtasks/crontab).",
	Long:  "Requires root flag --ping-http-addr. Chdirs to InstallRoot and takes a ensure lock. Use --from-cron for cron.",
	RunE:  cmds.EnsureKeepaliveCmdRunE,
}

func init() {
	GenConfigCmd.Flags().String("admin-endpoints", "",
		"Admin service endpoints, separated by ; (e.g. host1:port1;host2:port2)")
	GenConfigCmd.Flags().Uint64("cloud-id", 0, "Cloud ID (bk_cloud_id)")
	GenConfigCmd.Flags().String("local-ip", "", "Probe local IP address")
	GenConfigCmd.Flags().String(
		"local-ip-interface",
		"",
		"Preferred local interface name when auto-detecting --local-ip (default: use built-in default)",
	)
	GenConfigCmd.Flags().StringP("output", "o", "", "Output config file path (default: stdout)")
	GenConfigCmd.Flags().Duration(
		"timeout",
		cmds.DefaultGenConfigTimeout,
		"Timeout for fetching config from admin (non-positive falls back to default)",
	)
	GenConfigCmd.Flags().Duration(
		"lock-timeout",
		cmds.DefaultGenConfigLockTimeout,
		"Timeout for waiting the output config file lock (non-positive falls back to default)",
	)
	GenConfigCmd.Flags().String(
		"clear-port",
		"",
		"Ports to exclude from collection, persisted as clearPorts; empty value clears the list",
	)
	GenConfigCmd.Flags().Bool(
		"reload",
		false,
		"After writing the config file, signal the running probe to reload it",
	)

	EnsureCmd.Flags().BoolVar(&cmds.FromCron, "from-cron", false,
		"Kept for schtasks/crontab compatibility; currently does not change ensure behavior")
	EnsureKeepaliveCmd.Flags().BoolVar(&cmds.FromCron, "from-cron", false,
		"Invoked by schtasks/crontab; skip restart when keepalive is already running")
	// --ping-http-addr is the root persistent flag; ensure-keepalive reads it from the command line.
}
