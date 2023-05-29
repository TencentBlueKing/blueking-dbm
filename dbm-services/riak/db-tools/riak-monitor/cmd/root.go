package cmd

import (
	"os"

	"github.com/spf13/cobra"
	"golang.org/x/exp/slog"
)

var rootCmd = &cobra.Command{
	Use:   "riak-monitor",
	Short: "riak-monitor",
}

func init() {
	// rootCmd.PersistentFlags().StringP("config", "c", "", "config file")
	// _ = viper.BindPFlag("config", rootCmd.PersistentFlags().Lookup("config"))
}

// Execute TODO
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("start", err)
		os.Exit(1)
	}
}
