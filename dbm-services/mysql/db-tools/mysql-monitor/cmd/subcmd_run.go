package cmd

import (
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/mainloop"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
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
			slog.Error("run monitor load items", slog.String("error", err.Error()))
			return err
		}

		err = mainloop.Run(false)
		if err != nil {
			slog.Error("run monitor items", slog.String("error", err.Error()))
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
