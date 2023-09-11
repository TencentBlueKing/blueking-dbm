package cmd

import (
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

var subCmdDisableAll = &cobra.Command{
	Use:   "disable-all",
	Short: "disable-all items",
	Long:  "disable-all items",
	RunE: func(cmd *cobra.Command, args []string) error {
		configPath := viper.GetString("disable-config")
		if !filepath.IsAbs(configPath) {
			cwd, err := os.Getwd()
			if err != nil {
				slog.Error("disable-all get config abs path", err)
				return err
			}
			configPath = filepath.Join(cwd, configPath)
		}
		configFileDir, configFileName := filepath.Split(configPath)

		err := config.InitConfig(configPath)
		if err != nil {
			return err
		}
		initLogger(config.MonitorConfig.Log)

		emptyItemsConfig, err := os.CreateTemp("/tmp", "empty-items.yaml")
		if err != nil {
			slog.Error("disable-all create empty items config", slog.String("error", err.Error()))
			return err
		}
		defer func() {
			_ = emptyItemsConfig.Close()
			_ = os.Remove(emptyItemsConfig.Name())
		}()
		slog.Info("disable-all create empty items config success")

		config.MonitorConfig.ItemsConfigFile = emptyItemsConfig.Name()

		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("disable-all load items", err)
			return err
		}

		disableDbUp := viper.GetBool("with-db-up")
		if !disableDbUp {
			config.InjectMonitorDbUpItem()
		}
		config.InjectMonitorHeartBeatItem()

		slog.Info("disable-all",
			slog.String("staff", viper.GetString("staff")))
		err = reschedule(configFileDir, configFileName, viper.GetString("disable-staff"))
		if err != nil {
			slog.Error("disable-all sub-cmd", slog.String("error", err.Error()))
			return err
		}

		return nil
	},
}

func init() {
	subCmdDisableAll.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdDisableAll.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("disable-config", subCmdDisableAll.PersistentFlags().Lookup("config"))

	subCmdDisableAll.PersistentFlags().StringP("staff", "", "", "staff name")
	_ = subCmdDisableAll.MarkPersistentFlagRequired("staff")
	_ = viper.BindPFlag("disable-staff", subCmdDisableAll.PersistentFlags().Lookup("staff"))

	subCmdDisableAll.PersistentFlags().BoolP("with-db-up", "", false, "also disable db-up")
	_ = viper.BindPFlag("with-db-up", subCmdDisableAll.PersistentFlags().Lookup("with-db-up"))

	rootCmd.AddCommand(subCmdDisableAll)
}
