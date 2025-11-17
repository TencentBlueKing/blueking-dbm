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
	"log"
	"os"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/version"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/handler"

	"github.com/spf13/cobra"
)

var configFilePath string

// ResetRun executes the reset subcommand
func ResetRun(cmd *cobra.Command, args []string) error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	// Set global configuration
	config.SetClusterConfig(clusterConfig)

	// Create MySQL cluster handler and process clusters
	clusterHdl := handler.NewMysqlClusterHandler()
	if err := clusterHdl.ResetAllMysqlClusters(); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to reset MySQL clusters: %s", err.Error())
	}

	return nil
}

func main() {
	rootCmd := &cobra.Command{
		Use:          "cluster",
		Short:        "cluster management tool",
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			return cmd.Help()
		},
	}
	rootCmd.CompletionOptions.DisableDefaultCmd = true

	versionCmd := &cobra.Command{
		Use:   "version",
		Short: "Print Version Information",
		Run: func(cmd *cobra.Command, args []string) {
			version.Print("DBHA cluster")
		},
	}

	resetCmd := &cobra.Command{
		Use:   "reset",
		Short: "Reset clusters state according to configuration file",
		RunE:  ResetRun,
	}
	resetCmd.PersistentFlags().StringVarP(&configFilePath, "config", "c",
		"./etc/cluster.yaml", "Path to configuration file")

	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(resetCmd)

	if err := rootCmd.Execute(); err != nil {
		log.Printf("failed to execute cluster command: %v", err)
		os.Exit(1)
	}
}
