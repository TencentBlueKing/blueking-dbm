package cmd

import (
	"fmt"
	"strings"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

var subCmdClean = &cobra.Command{
	Use:   "clean",
	Short: "clean checksum entry",
	Long:  "clean checksum entry",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.InitConfig(viper.GetString("clean-config"))
		if err != nil {
			return err
		}

		manager := ma.NewManager(config.ChecksumConfig.ApiUrl)
		entries, err := manager.Entries()
		if err != nil {
			slog.Error("clean list entries", err)
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
		return nil
	},
}

func init() {
	subCmdClean.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdClean.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("clean-config", subCmdClean.PersistentFlags().Lookup("config"))

	rootCmd.AddCommand(subCmdClean)
}
