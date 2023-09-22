package main

import (
	"os"

	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/core/config"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// main bkconfigcli command
func main() {
	model.DB.Init()
	defer model.DB.Close()
	Execute()
}

var rootCmd = &cobra.Command{
	Use:   "bkconfigcli",
	Short: "bkconfigcli go binary",
	Long:  "bkconfigcli go binary",
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		_, _ = os.Stderr.WriteString(err.Error() + "\n")
		os.Exit(1)
	}
}

func init() {
	// init db config
	config.InitConfig("config")

	// rootCmd global flags
	rootCmd.PersistentFlags().String("namespace", "", "namespace")
	_ = viper.BindPFlag("namespace", rootCmd.PersistentFlags().Lookup("namespace"))

	rootCmd.PersistentFlags().String("conf-type", "", "conf_type")
	_ = viper.BindPFlag("conf-type", rootCmd.PersistentFlags().Lookup("conf-type"))

	rootCmd.PersistentFlags().String("conf-file", "", "conf_file")
	_ = viper.BindPFlag("conf-file", rootCmd.PersistentFlags().Lookup("conf-file"))

	rootCmd.PersistentFlags().Int("bk-biz-id", 0, "0 means plat, -1 means all bk_biz_id/cluster's password")
	_ = viper.BindPFlag("bk-biz-id", rootCmd.PersistentFlags().Lookup("bk-biz-id"))

	rootCmd.PersistentFlags().StringSlice("conf-name", []string{}, "conf_name")
	_ = viper.BindPFlag("conf-name", rootCmd.PersistentFlags().Lookup("conf-name"))

	rootCmd.PersistentFlags().String("level-value", "", "level_name=level_value")
	_ = viper.BindPFlag("level-value", rootCmd.PersistentFlags().Lookup("level-value"))

	rootCmd.PersistentFlags().String("old-key", "", "old key")
	_ = viper.BindPFlag("old-key", rootCmd.PersistentFlags().Lookup("old-key"))

	// queryCmd flags
	queryCmd.Flags().Bool("decrypt", false, "wait task done")
	_ = viper.BindPFlag("decrypt", queryCmd.Flags().Lookup("decrypt"))

	// updateCmd flags
	updateCmd.Flags().String("new-key", "", "new-key")
	_ = viper.BindPFlag("new-key", updateCmd.Flags().Lookup("new-key"))

	rootCmd.AddCommand(queryCmd)
	rootCmd.AddCommand(updateCmd)
}
