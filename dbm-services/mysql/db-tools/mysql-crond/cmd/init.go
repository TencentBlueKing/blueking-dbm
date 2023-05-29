package cmd

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

// ExecutableName TODO
var ExecutableName string

func init() {
	rootCmd.Flags().StringP("config", "c", "", "runtime config file")
	rootCmd.Flags().BoolP("without-heart-beat", "", false, "disable heart beat")
	_ = rootCmd.MarkFlagRequired("config")
	_ = viper.BindPFlag("config", rootCmd.Flags().Lookup("config"))
	_ = viper.BindPFlag("without-heart-beat", rootCmd.Flags().Lookup("without-heart-beat"))

	ex, _ := os.Executable()
	ExecutableName = filepath.Base(ex)
}
