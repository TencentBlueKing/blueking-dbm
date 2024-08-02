package cmd

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

// ExecutableName TODO
var ExecutableName string

func init() {
	rootCmd.PersistentFlags().StringP("config", "c", "runtime.yaml", "runtime config file")
	//_ = rootCmd.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("config", rootCmd.Flags().Lookup("config"))

	rootCmd.Flags().BoolP("without-heart-beat", "", false, "disable heart beat")
	_ = viper.BindPFlag("without-heart-beat", rootCmd.Flags().Lookup("without-heart-beat"))

	ex, _ := os.Executable()
	ExecutableName = filepath.Base(ex)
}
