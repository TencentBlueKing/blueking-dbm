package cmd

import (
	"log/slog"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var subCmdReschedule = &cobra.Command{
	Use:   "reschedule",
	Short: "reschedule mysql-crond entry",
	Long:  "reschedule mysql-crond entry",
	RunE: func(cmd *cobra.Command, args []string) error {
		/*
			就只有这个子命令需要这样把配置转换成绝对路径
			因为注册到crond后cwd是其他目录了
		*/
		configPath := viper.GetString("reschedule-config")
		if !filepath.IsAbs(configPath) {
			cwd, err := os.Getwd()
			if err != nil {
				slog.Error("reschedule get config abs path", slog.String("error", err.Error()))
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

		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("reschedule load items", slog.String("error", err.Error()))
			return err
		}

		config.InjectMonitorDbUpItem()
		config.InjectMonitorHeartBeatItem()

		err = config.WriteMonitorItemsBack()
		if err != nil {
			slog.Error("reschedule write back items", slog.String("error", err.Error()))
			return err
		}

		err = reschedule(configFileDir, configFileName, viper.GetString("reschedule-staff"))
		if err != nil {
			slog.Error("reschedule sub-cmd", slog.String("error", err.Error()))
			return err
		}

		return nil
	},
}

func init() {
	subCmdReschedule.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdReschedule.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("reschedule-config", subCmdReschedule.PersistentFlags().Lookup("config"))

	subCmdReschedule.PersistentFlags().StringP("staff", "", "", "staff name")
	_ = subCmdReschedule.MarkPersistentFlagRequired("staff")
	_ = viper.BindPFlag("reschedule-staff", subCmdReschedule.PersistentFlags().Lookup("staff"))

	rootCmd.AddCommand(subCmdReschedule)
}
