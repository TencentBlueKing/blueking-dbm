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
	"os"

	"dbm-services/common/dbha-v2/internal/admin"
	"dbm-services/common/dbha-v2/pkg/logger"

	_ "dbm-services/common/dbha-v2/internal/provider/alldesc"

	"github.com/spf13/cobra"
)

func run(args []string) int {
	// cobra falls back to os.Args[1:] when the args slice is nil, which is the
	// test binary's own command line under go test.
	if args == nil {
		args = []string{}
	}

	rootCmd := &cobra.Command{
		Use:          "admin",
		Short:        "DBHA Admin Server",
		SilenceUsage: true,
		RunE:         admin.Run,
	}

	rootCmd.PersistentFlags().StringVarP(&admin.ConfigFilePath, "config", "c", "./etc/admin.yaml", "")
	rootCmd.CompletionOptions.DisableDefaultCmd = true

	rootCmd.AddCommand(admin.VersionCmd)
	rootCmd.AddCommand(admin.MigrateCmd)
	rootCmd.AddCommand(admin.HealthCmd)
	rootCmd.AddCommand(admin.StartCmd)
	rootCmd.AddCommand(admin.DaemonStartCmd)
	rootCmd.AddCommand(admin.StopCmd)
	rootCmd.AddCommand(admin.RestartCmd)
	rootCmd.AddCommand(admin.ReloadCmd)

	rootCmd.SetArgs(args)

	if err := rootCmd.Execute(); err != nil {
		logger.Error("failed to start admin server, errmsg: %s", err)
		return 1
	}

	return 0
}

func main() {
	os.Exit(run(os.Args[1:]))
}
