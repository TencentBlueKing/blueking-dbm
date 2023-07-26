package cmd

import (
	"strings"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// 清理mysql-crond中riak监控entry，但不包括硬编码。如果要退出监控，可访问mysql-crond的quit接口
var subCmdClean = &cobra.Command{
	Use:   "clean",
	Short: "clean all mysql-crond entry",
	Long:  "clean all mysql-crond entry",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.InitConfig(viper.GetString("clean-config"))
		if err != nil {
			return err
		}
		initLogger(config.MonitorConfig.Log)
		// 通过mysql-crond的接口删除entry
		manager := ma.NewManager(config.MonitorConfig.ApiUrl)
		// 获取mysql-crond注册的所有entry
		entries, err := manager.Entries()
		if err != nil {
			slog.Error("clean list entries", err)
			return err
		}
		for _, entry := range entries {
			// riak监控的entry，排除硬编码的entry，注意此接口会持久化到crond的配置文件jobs-config.yaml
			if strings.HasPrefix(entry.Job.Name, "riak-") &&
				!strings.Contains(entry.Job.Name, "hardcode") {
				eid, err := manager.Delete(entry.Job.Name, true)
				if err != nil {
					slog.Error(
						"delete entry", err,
						slog.String("name", entry.Job.Name),
					)
					return err
				}
				slog.Info(
					"delete entry",
					slog.String("name", entry.Job.Name),
					slog.Int("ID", eid),
				)
			}
		}
		return nil
	},
}

func init() {
	subCmdClean.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdClean.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("clean-config", subCmdClean.PersistentFlags().Lookup("config"))

	rootCmd.AddCommand(subCmdClean)

}
