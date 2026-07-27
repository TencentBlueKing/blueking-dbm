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

package main

import (
	"fmt"
	"os"

	"dbm-services/common/dbha-v2/internal/probe"

	_ "dbm-services/common/dbha-v2/internal/provider/allprobe"

	"github.com/spf13/cobra"
)

func run(args []string) int {
	// cobra falls back to os.Args[1:] when the args slice is nil, which is the
	// test binary's own command line under go test.
	if args == nil {
		args = []string{}
	}

	pingAddr, enabled, err := probe.ExtractPingHTTPAddrFromArgs(args)
	if err != nil {
		fmt.Println("failed to execute probe. errmsg:", err.Error())
		return 1
	}
	if enabled {
		if err := probe.RunKeepaliveMode(pingAddr, args); err != nil {
			fmt.Println("failed to execute probe. errmsg:", err.Error())
			return 1
		}
		return 0
	}

	rootCmd := &cobra.Command{
		Use:           "probe",
		Short:         "DBHA Probe",
		SilenceUsage:  true,
		SilenceErrors: true,
		RunE:          probe.Run,
	}

	rootCmd.PersistentFlags().StringVarP(&probe.ConfigFilePath, "config", "c", "./etc/probe.yaml", "")
	rootCmd.PersistentFlags().StringVar(
		&probe.PingHTTPAddr,
		"ping-http-addr",
		"",
		"Ping HTTP server listen address (e.g. 127.0.0.1:18080)",
	)
	rootCmd.CompletionOptions.DisableDefaultCmd = true

	rootCmd.AddCommand(probe.VersionCmd)
	rootCmd.AddCommand(probe.HealthCmd)
	rootCmd.AddCommand(probe.StartCmd)
	rootCmd.AddCommand(probe.DaemonStartCmd)
	rootCmd.AddCommand(probe.StopCmd)
	rootCmd.AddCommand(probe.RestartCmd)
	rootCmd.AddCommand(probe.ReloadCmd)
	rootCmd.AddCommand(probe.GenConfigCmd)
	rootCmd.AddCommand(probe.EnsureCmd)
	rootCmd.AddCommand(probe.EnsureKeepaliveCmd)

	rootCmd.SetArgs(args)

	if err := rootCmd.Execute(); err != nil {
		fmt.Println("failed to execute probe. errmsg:", err.Error())
		return 1
	}

	return 0
}

func main() {
	os.Exit(run(os.Args[1:]))
}
