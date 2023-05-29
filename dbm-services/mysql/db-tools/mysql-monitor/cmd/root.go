package cmd

import (
	"log/slog"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "mysql-monitor",
	Short: "mysql-monitor",
}

func init() {
	// rootCmd.PersistentFlags().StringP("config", "c", "", "config file")
	// _ = viper.BindPFlag("config", rootCmd.PersistentFlags().Lookup("config"))
}

// Execute TODO
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("start", slog.String("error", err.Error()))
		os.Exit(1)
	}
}
