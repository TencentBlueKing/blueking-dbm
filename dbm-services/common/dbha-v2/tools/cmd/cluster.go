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
	"io"
	"log"
	"os"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/version"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/handler"

	"github.com/spf13/cobra"
	"go.uber.org/zap"
)

func init() {
	// Suppress debug logs
	logger.SetLogger(&nopLogger{})
	log.SetOutput(io.Discard)
}

type nopLogger struct{}

func (n *nopLogger) OriginLogger() *zap.Logger        { return zap.NewNop() }
func (n *nopLogger) Debug(string, ...any)             {}
func (n *nopLogger) Info(string, ...any)              {}
func (n *nopLogger) Warn(string, ...any)              {}
func (n *nopLogger) Error(string, ...any)             {}
func (n *nopLogger) Fatal(format string, args ...any) { log.Fatalf(format, args...) }

const (
	ClusterTypeMySQL        = "mysql"
	ClusterTypeTenDBCluster = "tendbcluster"
	typeOptionsHint         = "please enter one of the following options: mysql, tendbcluster"
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

	clusterType, _ := cmd.Flags().GetString("type")

	switch clusterType {
	case ClusterTypeMySQL:
		// Create MySQL cluster handler and process clusters
		clusterHdl := handler.NewMysqlClusterHandler()
		if err := clusterHdl.ResetAllMysqlClusters(); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to reset MySQL clusters: %s", err.Error())
		}
	case ClusterTypeTenDBCluster:
		// Create TenDB Cluster handler and process clusters
		tenDBClusterHdl := handler.NewTenDBClusterHandler()
		if err := tenDBClusterHdl.ResetAllTenDBClusters(); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to reset TenDB clusters: %s", err.Error())
		}
	default:
		return gerrors.Newf(gerrors.Failure, typeOptionsHint)
	}

	return nil
}

// ShowDomainRun executes the show domain subcommand
func ShowDomainRun(cmd *cobra.Command, args []string) error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	config.SetClusterConfig(clusterConfig)

	clusterType, _ := cmd.Flags().GetString("type")

	switch clusterType {
	case ClusterTypeMySQL:
		clusterHdl := handler.NewMysqlClusterHandler()
		return clusterHdl.ShowAllMysqlClustersDomain()
	case ClusterTypeTenDBCluster:
		tenDBClusterHdl := handler.NewTenDBClusterHandler()
		return tenDBClusterHdl.ShowAllTenDBClustersDomain()
	default:
		return gerrors.Newf(gerrors.Failure, typeOptionsHint)
	}
}

// ShowNodesRun executes the show nodes subcommand
func ShowNodesRun(cmd *cobra.Command, args []string) error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	config.SetClusterConfig(clusterConfig)

	clusterType, _ := cmd.Flags().GetString("type")

	switch clusterType {
	case ClusterTypeMySQL:
		clusterHdl := handler.NewMysqlClusterHandler()
		return clusterHdl.ShowAllMysqlClustersNodes()
	case ClusterTypeTenDBCluster:
		tenDBClusterHdl := handler.NewTenDBClusterHandler()
		return tenDBClusterHdl.ShowAllTenDBClustersNodes()
	default:
		return gerrors.Newf(gerrors.Failure, typeOptionsHint)
	}
}

// ShowReplicationRun executes the show replication subcommand
func ShowReplicationRun(cmd *cobra.Command, args []string) error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	config.SetClusterConfig(clusterConfig)

	clusterType, _ := cmd.Flags().GetString("type")

	switch clusterType {
	case ClusterTypeMySQL:
		clusterHdl := handler.NewMysqlClusterHandler()
		return clusterHdl.ShowAllMysqlClustersReplication()
	case ClusterTypeTenDBCluster:
		tenDBClusterHdl := handler.NewTenDBClusterHandler()
		return tenDBClusterHdl.ShowAllTenDBClustersReplication()
	default:
		return gerrors.Newf(gerrors.Failure, typeOptionsHint)
	}
}

// ShowRoutingRun executes the show routing subcommand
func ShowRoutingRun(cmd *cobra.Command, args []string) error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	config.SetClusterConfig(clusterConfig)

	clusterType, _ := cmd.Flags().GetString("type")

	switch clusterType {
	case ClusterTypeMySQL:
		clusterHdl := handler.NewMysqlClusterHandler()
		return clusterHdl.ShowAllMysqlClustersRouting()
	case ClusterTypeTenDBCluster:
		tenDBClusterHdl := handler.NewTenDBClusterHandler()
		return tenDBClusterHdl.ShowAllTenDBClustersRouting()
	default:
		return gerrors.Newf(gerrors.Failure, typeOptionsHint)
	}
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
	resetCmd.Flags().String("type", "", "cluster type")
	resetCmd.MarkFlagRequired("type")
	resetCmd.PersistentFlags().StringVarP(&configFilePath, "config", "c",
		"./etc/cluster.yaml", "Path to configuration file")

	showCmd := &cobra.Command{
		Use:   "show",
		Short: "Show cluster information",
		RunE: func(cmd *cobra.Command, args []string) error {
			return cmd.Help()
		},
	}
	showCmd.PersistentFlags().StringVarP(&configFilePath, "config", "c",
		"./etc/cluster.yaml", "Path to configuration file")
	showCmd.PersistentFlags().String("type", "", "cluster type (mysql, tendbcluster)")
	showCmd.MarkPersistentFlagRequired("type")

	showDomainCmd := &cobra.Command{
		Use:   "domain",
		Short: "Show domain binding information (JSON format)",
		RunE:  ShowDomainRun,
	}

	showNodesCmd := &cobra.Command{
		Use:   "nodes",
		Short: "Show all nodes status and role information (JSON format)",
		RunE:  ShowNodesRun,
	}

	showReplicationCmd := &cobra.Command{
		Use:   "replication",
		Short: "Show master-slave replication status (JSON format)",
		RunE:  ShowReplicationRun,
	}

	showRoutingCmd := &cobra.Command{
		Use:   "routing",
		Short: "Show routing info: mysql.servers for tendbcluster, proxy backends for mysql (JSON format)",
		RunE:  ShowRoutingRun,
	}

	showCmd.AddCommand(showDomainCmd)
	showCmd.AddCommand(showNodesCmd)
	showCmd.AddCommand(showReplicationCmd)
	showCmd.AddCommand(showRoutingCmd)

	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(resetCmd)
	rootCmd.AddCommand(showCmd)

	if err := rootCmd.Execute(); err != nil {
		log.Printf("failed to execute cluster command: %v", err)
		os.Exit(1)
	}
}
