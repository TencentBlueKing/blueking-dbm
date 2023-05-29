package cmd

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/main_loop"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

var subCmdRun = &cobra.Command{
	Use:   "run",
	Short: "run monitor items",
	Long:  "run monitor items",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.InitConfig(viper.GetString("run-config"))
		if err != nil {
			return err
		}
		initLogger(config.MonitorConfig.Log)

		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("run monitor load items", err)
			return err
		}

		err = main_loop.Run(false)
		if err != nil {
			slog.Error("run monitor items", err)
			return err
		}
		return nil
	},
}

func init() {
	subCmdRun.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdRun.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("run-config", subCmdRun.PersistentFlags().Lookup("config"))

	subCmdRun.PersistentFlags().StringSliceP("items", "", nil, "run items")
	_ = subCmdRun.MarkPersistentFlagRequired("items")
	_ = viper.BindPFlag("run-items", subCmdRun.PersistentFlags().Lookup("items"))

	rootCmd.AddCommand(subCmdRun)
}
