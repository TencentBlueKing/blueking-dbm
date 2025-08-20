package cmd

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var subCmdDemand = &cobra.Command{
	Use:   "demand",
	Short: "demand checksum",
	Long:  "demand checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		return generateRun(config.DemandMode, viper.GetString("demand-config"))
	},
}

func init() {
	subCmdDemand.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdDemand.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("demand-config", subCmdDemand.PersistentFlags().Lookup("config"))

	subCmdDemand.PersistentFlags().Int64P("ticket-id", "", 0, "unique id for each demand")
	_ = subCmdDemand.MarkPersistentFlagRequired("ticket-id")
	_ = viper.BindPFlag("ticket-id", subCmdDemand.PersistentFlags().Lookup("ticket-id"))

	rootCmd.AddCommand(subCmdDemand)
}
