package cmd

import (
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/mainloop"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

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

		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("run hardcode monitor load items", slog.String("error", err.Error()))
			return err
		}

		err = mainloop.Run(true)
		if err != nil {
			slog.Error("run monitor hardcode items", slog.String("error", err.Error()))
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
