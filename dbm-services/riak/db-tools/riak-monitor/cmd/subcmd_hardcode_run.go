package cmd

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"
	"dbm-services/riak/db-tools/riak-monitor/pkg/mainloop"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// 硬编码，监控启动后基础的定时任务，包括数据库是否启动、心跳上报
var subCmdHardCodeRun = &cobra.Command{
	Use:   "hardcode-run",
	Short: "run hardcode monitor items",
	Long:  "run hardcode monitor items",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.InitConfig(viper.GetString("hard-run-config"))
		if err != nil {
			return err
		}
		initLogger(config.MonitorConfig.Log)
		// 加载监控items-config.yaml配置文件
		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("run hardcode monitor load items", err)
			return err
		}
		// 执行监控项对应的函数
		err = mainloop.Run(true)
		if err != nil {
			slog.Error("run monitor hardcode items", err)
			return err
		}
		return nil
	},
}

func init() {
	subCmdHardCodeRun.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdHardCodeRun.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("hard-run-config", subCmdHardCodeRun.PersistentFlags().Lookup("config"))

	subCmdHardCodeRun.PersistentFlags().StringSliceP("items", "", nil, "run items")
	_ = subCmdHardCodeRun.MarkPersistentFlagRequired("items")
	_ = viper.BindPFlag("hardcode-items", subCmdHardCodeRun.PersistentFlags().Lookup("items"))

	rootCmd.AddCommand(subCmdHardCodeRun)
}
