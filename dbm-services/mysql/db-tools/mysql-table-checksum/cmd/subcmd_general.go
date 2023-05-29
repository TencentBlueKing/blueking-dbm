package cmd

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var subCmdGeneral = &cobra.Command{
	Use:   "general",
	Short: "general checksum",
	Long:  "general checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		return generateRun(config.GeneralMode, viper.GetString("general-config"))
	},
}

func init() {
	subCmdGeneral.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdGeneral.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("general-config", subCmdGeneral.PersistentFlags().Lookup("config"))

	rootCmd.AddCommand(subCmdGeneral)
}
