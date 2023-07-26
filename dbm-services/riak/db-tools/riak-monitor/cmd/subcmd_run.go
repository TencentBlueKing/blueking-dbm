package cmd

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"
	"dbm-services/riak/db-tools/riak-monitor/pkg/mainloop"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// 根据配置文件以及指定的item，运行监控
var subCmdRun = &cobra.Command{
	Use:   "run",
	Short: "run monitor items",
	Long:  "run monitor items",
	RunE: func(cmd *cobra.Command, args []string) error {
		// 配置初始化
		err := config.InitConfig(viper.GetString("run-config"))
		if err != nil {
			return err
		}
		// 初始化日志配置
		initLogger(config.MonitorConfig.Log)
		// 加载监控items-config.yaml配置文件
		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("run monitor load items", err)
			return err
		}
		// 执行监控项
		err = mainloop.Run(false)
		if err != nil {
			slog.Error("msg", "run monitor items", err)
			return err
		}
		return nil
	},
}

func init() {
	// 配置文件
	subCmdRun.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdRun.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("run-config", subCmdRun.PersistentFlags().Lookup("config"))
	// 指定items
	subCmdRun.PersistentFlags().StringSliceP("items", "", nil, "run items")
	_ = subCmdRun.MarkPersistentFlagRequired("items")
	_ = viper.BindPFlag("run-items", subCmdRun.PersistentFlags().Lookup("items"))

	rootCmd.AddCommand(subCmdRun)
}
