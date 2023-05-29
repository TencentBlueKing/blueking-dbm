package cmd

import (
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
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
				slog.Error("reschedule get config abs path", err)
				return err
			}
			configPath = filepath.Join(cwd, configPath)
		}

		err := config.InitConfig(configPath)
		if err != nil {
			return err
		}

		manager := ma.NewManager(config.ChecksumConfig.ApiUrl)
		entries, err := manager.Entries()
		if err != nil {
			slog.Error("reschedule list entries", err)
			return err
		}

		for _, entry := range entries {
			if strings.HasPrefix(
				entry.Job.Name,
				fmt.Sprintf("mysql-checksum-%d", config.ChecksumConfig.Port),
			) {
				eid, err := manager.Delete(entry.Job.Name, true)
				if err != nil {
					slog.Error(
						"reschedule delete entry", err,
						slog.String("name", entry.Job.Name),
					)
					return err
				}
				slog.Info(
					"reschedule delete entry",
					slog.String("name", entry.Job.Name),
					slog.Int("ID", eid),
				)
			}
		}

		eid, err := manager.CreateOrReplace(
			ma.JobDefine{
				Name:    fmt.Sprintf("mysql-checksum-%d", config.ChecksumConfig.Port),
				Command: executable,
				Args: []string{
					"general",
					"--config", configPath,
				},
				Schedule: config.ChecksumConfig.Schedule,
				Creator:  viper.GetString("staff"),
				Enable:   true,
			}, true,
		)
		if err != nil {
			slog.Error("reschedule add entry", err)
			return err
		}
		slog.Info("reschedule add entry", slog.Int("entry id", eid))

		return nil
	},
}

func init() {
	subCmdReschedule.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdReschedule.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("reschedule-config", subCmdReschedule.PersistentFlags().Lookup("config"))

	subCmdReschedule.PersistentFlags().StringP("staff", "", "", "staff name")
	_ = subCmdReschedule.MarkPersistentFlagRequired("staff")
	_ = viper.BindPFlag("staff", subCmdReschedule.PersistentFlags().Lookup("staff"))

	rootCmd.AddCommand(subCmdReschedule)
}
