package cmd

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"io"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var subCmdEnable = &cobra.Command{
	Use:   "enable",
	Short: "enable mysql checksum",
	Long:  "enable mysql checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		configPath := viper.GetString("enable-config")
		if !filepath.IsAbs(configPath) {
			cwd, _ := os.Getwd()
			configPath = filepath.Join(cwd, configPath)
		}

		return enableSwitch(configPath, true)
	},
}

var subCmdDisable = &cobra.Command{
	Use:   "disable",
	Short: "disable mysql checksum",
	Long:  "disable mysql checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		configPath := viper.GetString("disable-config")
		if !filepath.IsAbs(configPath) {
			cwd, _ := os.Getwd()
			configPath = filepath.Join(cwd, configPath)
		}

		return enableSwitch(configPath, false)
	},
}

func enableSwitch(fp string, enable bool) error {
	f, err := os.OpenFile(fp, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	b, err := io.ReadAll(f)
	if err != nil {
		return err
	}

	cfg := config.Config{}
	if err := yaml.Unmarshal(b, &cfg); err != nil {
		return err
	}

	cfg.Enable = enable
	b, err = yaml.Marshal(cfg)
	if err != nil {
		return err
	}

	_, err = f.Write(b)
	if err != nil {
		return err
	}

	return nil
}

func init() {
	subCmdEnable.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdGenConfig.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("enable-config", subCmdEnable.PersistentFlags().Lookup("config"))

	subCmdDisable.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdDisable.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("disable-config", subCmdDisable.PersistentFlags().Lookup("config"))

	rootCmd.AddCommand(subCmdEnable)
	rootCmd.AddCommand(subCmdDisable)
}
