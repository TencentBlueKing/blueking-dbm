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
	"dbm-services/common/dbha-v2/internal/admin"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/spf13/cobra"
)

func main() {
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

	if err := rootCmd.Execute(); err != nil {
		logger.Error("failed to start admin server. errmsg:%s", err.Error())
		return
	}

}
