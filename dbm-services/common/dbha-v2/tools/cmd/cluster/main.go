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
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/version"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/handler"

	"github.com/spf13/cobra"
)

var configFilePath string
var sessionWhere string

// clusterTypeOptions lists every --type value reset and show accept.
func clusterTypeOptions() []string {
	return config.ClusterTypeOptions()
}

func loadAndSetClusterConfig() error {
	if configFilePath == "" {
		return gerrors.Newf(gerrors.Failure, "config file path is required")
	}

	clusterConfig, err := config.LoadConfig(configFilePath)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to load config: %s", err.Error())
	}

	config.SetClusterConfig(clusterConfig)
	return nil
}

func handlersForType(clusterType string) ([]handler.ClusterHandler, error) {
	switch {
	case strings.EqualFold(clusterType, config.DbTypeMysql.String()):
		return []handler.ClusterHandler{
			handler.NewMysqlClusterHandler(),
			handler.NewTenDBClusterHandler(),
		}, nil
	case strings.EqualFold(clusterType, config.ClusterTypeTendbha.String()):
		return []handler.ClusterHandler{handler.NewMysqlClusterHandler()}, nil
	case strings.EqualFold(clusterType, config.ClusterTypeTendbCluster.String()):
		return []handler.ClusterHandler{handler.NewTenDBClusterHandler()}, nil
	case strings.EqualFold(clusterType, config.DbTypeRedis.String()):
		return []handler.ClusterHandler{handler.NewRedisClusterHandler()}, nil
	default:
		redisType, ok := config.NormalizeRedisClusterType(clusterType)
		if !ok {
			return nil, gerrors.Newf(gerrors.Failure, "%s", typeOptionsHint(clusterTypeOptions()))
		}
		return []handler.ClusterHandler{handler.NewRedisClusterHandlerOfType(redisType)}, nil
	}
}

func runOnHandlers(cmd *cobra.Command, fn func(handler.ClusterHandler) error) error {
	if err := loadAndSetClusterConfig(); err != nil {
		return err
	}

	clusterType, _ := cmd.Flags().GetString("type")
	handlers, err := handlersForType(clusterType)
	if err != nil {
		return err
	}

	for _, hdl := range handlers {
		if err := fn(hdl); err != nil {
			return err
		}
	}
	return nil
}

func runShow(cmd *cobra.Command, fn func([]handler.ClusterHandler) error) error {
	if err := loadAndSetClusterConfig(); err != nil {
		return err
	}

	clusterType, _ := cmd.Flags().GetString("type")
	handlers, err := handlersForType(clusterType)
	if err != nil {
		return err
	}

	return fn(handlers)
}

// typeOptionsHint renders the accepted --type values as an error message.
func typeOptionsHint(options []string) string {
	return "please enter one of the following options: " + strings.Join(options, ", ")
}

// typeFlagUsage renders the accepted --type values as flag help.
func typeFlagUsage(options []string) string {
	return "cluster type (" + strings.Join(options, ", ") + ")"
}

// ResetRun runs the reset subcommand for the selected cluster type.
func ResetRun(cmd *cobra.Command, args []string) error {
	return runOnHandlers(cmd, func(hdl handler.ClusterHandler) error {
		return hdl.Reset()
	})
}

// ShowDomainRun runs the show domain subcommand for the selected cluster type.
func ShowDomainRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, handler.PrintShowDomain)
}

// ShowNodesRun runs the show nodes subcommand for the selected cluster type.
func ShowNodesRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, handler.PrintShowNodes)
}

// ShowReplicationRun runs the show replication subcommand for the selected cluster type.
func ShowReplicationRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, handler.PrintShowReplication)
}

// ShowClbRun runs the show clb subcommand for the selected cluster type.
func ShowClbRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, handler.PrintShowClb)
}

// ShowRoutingRun runs the show routing subcommand for the selected cluster type.
func ShowRoutingRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, handler.PrintShowRouting)
}

// ShowSessionRun runs the show session subcommand for the selected cluster type.
func ShowSessionRun(cmd *cobra.Command, args []string) error {
	return runShow(cmd, func(handlers []handler.ClusterHandler) error {
		return handler.PrintShowSession(handlers, sessionWhere)
	})
}

func newResetCmd() *cobra.Command {
	resetCmd := &cobra.Command{
		Use:   "reset",
		Short: "Reset clusters state according to configuration file",
		RunE:  ResetRun,
	}
	resetCmd.Flags().String("type", "", typeFlagUsage(clusterTypeOptions()))
	_ = resetCmd.MarkFlagRequired("type")
	resetCmd.PersistentFlags().StringVarP(&configFilePath, "config", "c",
		"./etc/cluster.yaml", "Path to configuration file")
	return resetCmd
}

func newShowCmd() *cobra.Command {
	showCmd := &cobra.Command{
		Use:   "show",
		Short: "Show cluster information",
		RunE: func(cmd *cobra.Command, args []string) error {
			return cmd.Help()
		},
	}
	showCmd.PersistentFlags().StringVarP(&configFilePath, "config", "c",
		"./etc/cluster.yaml", "Path to configuration file")
	showCmd.PersistentFlags().String("type", "", typeFlagUsage(clusterTypeOptions()))
	_ = showCmd.MarkPersistentFlagRequired("type")
	return showCmd
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
	rootCmd.PersistentFlags().IntVar(
		&handler.ClusterMaxConcurrency,
		"max-concurrency",
		handler.ClusterMaxConcurrency,
		"Maximum number of concurrent goroutines used by cluster operations",
	)

	versionCmd := &cobra.Command{
		Use:   "version",
		Short: "Print Version Information",
		Run: func(cmd *cobra.Command, args []string) {
			version.Print("DBHA cluster")
		},
	}

	showCmd := newShowCmd()

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
		Short: "Show redis replication: INFO replication or CLUSTER NODES (JSON format)",
		RunE:  ShowReplicationRun,
	}

	showRoutingCmd := &cobra.Command{
		Use:   "routing",
		Short: "Show routing info: twemproxy servers, predixy INFO Servers, or mysql.servers (JSON format)",
		RunE:  ShowRoutingRun,
	}

	showClbCmd := &cobra.Command{
		Use:   "clb",
		Short: "Show CLB binding information (JSON format)",
		RunE:  ShowClbRun,
	}

	showSessionCmd := &cobra.Command{
		Use:   "session",
		Short: "Show sessions: processlist for mysql, CLIENT LIST for redis (JSON format)",
		RunE:  ShowSessionRun,
	}
	showSessionCmd.Flags().StringVar(&sessionWhere, "where", "",
		"mysql: filter appended to processlist WHERE; redis: extra CLIENT LIST arguments (e.g. TYPE normal)")

	showCmd.AddCommand(showDomainCmd)
	showCmd.AddCommand(showNodesCmd)
	showCmd.AddCommand(showReplicationCmd)
	showCmd.AddCommand(showRoutingCmd)
	showCmd.AddCommand(showClbCmd)
	showCmd.AddCommand(showSessionCmd)

	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(newResetCmd())
	rootCmd.AddCommand(showCmd)

	if err := rootCmd.Execute(); err != nil {
		log.Printf("failed to execute cluster command: %v", err)
		os.Exit(1)
	}
}
