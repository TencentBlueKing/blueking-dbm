// Package cmd TODO
package cmd

import (
	"log"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// DbbackupVersion TODO
var DbbackupVersion = "undef"

var cnfFile string

var rootCmd = &cobra.Command{
	Use:     "dbbackup",
	Short:   "dbbackup go binary",
	Long:    "dbbackup go binary",
	Version: DbbackupVersion,
}

// Execute TODO
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		_, _ = os.Stderr.WriteString(err.Error() + "\n")
		os.Exit(1)
	}
}

func init() {
	// rootCmd
	// rootCmd.PersistentFlags().StringVarP(&cnfFile, "config", "c", "", "config file")
	// _ = rootCmd.MarkPersistentFlagRequired("config")

	rootCmd.AddCommand(dumpCmd)
	rootCmd.AddCommand(loadCmd)
	rootCmd.AddCommand(spiderCmd)
	rootCmd.AddCommand(migrateOldCmd)
}

// initConfig parse the configuration file of dbbackup to init a cfg
// confFile 可以是文件名，也可以带目录
func initConfig(confFile string, v interface{}) error {
	// logger.Log.Info("parse config file: begin")
	viper.SetConfigType("ini")
	if confFile != "" {
		viper.SetConfigFile(confFile)
	} else {
		viper.SetConfigName("config")

		// default: current run work_dir
		viper.AddConfigPath(".") // 搜索路径可以设置多个，viper 会根据设置顺序依次查找

		// default: exe relative dir
		executable, _ := os.Executable()
		executableDir := filepath.Dir(executable)
		defaultConfigDir := filepath.Join(executableDir, "./")
		viper.AddConfigPath(defaultConfigDir)

		// // default: /home/user/xxx dir
		// home, _ := homedir.Dir()
		// viper.AddConfigPath(home)
	}
	if err := viper.ReadInConfig(); err != nil {
		log.Fatalf("read config failed: %v", err)
	}
	err := viper.Unmarshal(v)
	if err != nil {
		log.Fatalf("parse config failed: %v", err)
	}
	logger.Log.Infof("initConfig success %s", viper.ConfigFileUsed())
	return nil
}
