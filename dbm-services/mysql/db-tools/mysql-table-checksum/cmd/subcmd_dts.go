package cmd

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var subCmdDtsMode = &cobra.Command{
	Use:   "dts-mode",
	Short: "dts-mode checksum",
	Long:  "dts-mode checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		return generateRun(config.DtsMode, viper.GetString("dts-mode-config"))
	},
}

func init() {
	subCmdDtsMode.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdDtsMode.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("dts-mode-config", subCmdDtsMode.PersistentFlags().Lookup("config"))

	subCmdDtsMode.PersistentFlags().StringP("uuid", "", "", "unique id for each dts-mode")
	_ = subCmdDtsMode.MarkPersistentFlagRequired("uuid")
	_ = viper.BindPFlag("uuid", subCmdDtsMode.PersistentFlags().Lookup("uuid"))

	rootCmd.AddCommand(subCmdDtsMode)
}
