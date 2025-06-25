// Package cmd TODO
package cmd

import (
	"dbm-services/common/reverseapi/pkg"
	"math"
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	meta "dbm-services/common/reverseapi/define/mysql"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// DbbackupVersion TODO
var DbbackupVersion = "undef"

var cnfFile string
var logFile string

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
		// todo try to kill child process(mydumper / myloader / xtrabackup)
		os.Exit(1)
	}
}

func init() {
	// rootCmd
	rootCmd.PersistentFlags().StringVar(&logFile, "log-dir", "",
		"log file path. default empty will log files to dir dbbackup/logs/")
	_ = viper.BindPFlag("log-dir", rootCmd.PersistentFlags().Lookup("log-dir"))

	// overwrite -h option
	rootCmd.PersistentFlags().BoolP("help", "", false, "help for this command")
	rootCmd.AddCommand(dumpCmd)
	rootCmd.AddCommand(loadCmd)
	rootCmd.AddCommand(spiderCmd)
	rootCmd.AddCommand(migrateOldCmd)
	rootCmd.AddCommand(dumpLogicalCmd)
	rootCmd.AddCommand(uploadCmd)
}

// initConfig parse the configuration file of dbbackup to init a cfg
// confFile 可以是文件名，也可以带目录
func initConfig(confFile string, cnf *config.BackupConfig, log *logrus.Logger) error {
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
	}
	if err := viper.ReadInConfig(); err != nil {
		log.Fatalf("dbbackup read config failed: %v", err)
	}
	err := viper.Unmarshal(cnf)
	if err != nil {
		log.Fatalf("parse config failed: %v", err)
	}
	// 如果是在 remote 上执行，common_config 中一般获取不到 is_standby，会忽略错误
	if instInfo, err := pkg.GetSelfInfo(cnf.Public.MysqlHost, cnf.Public.MysqlPort); err == nil {
		if instInfo.AccessLayer == meta.AccessLayerStorage && instInfo.InstanceInnerRole != "" {
			cnf.Public.MysqlRole = instInfo.InstanceInnerRole
			log.Infof("use role from common_config:%s, config:%s",
				instInfo.InstanceInnerRole, cnf.Public.MysqlRole)
		}
		if instInfo.AccessLayer == meta.AccessLayerStorage && !instInfo.IsStandBy {
			log.Infof("the standby flag from common_config is %v, not upload to backup system",
				instInfo.IsStandBy)
			//cnf.BackupClient.Enable = false
			// is_standby = false 且 EnableBackupClient = auto 则禁用备份客户端
			if cnf.BackupClient.EnableBackupClient == "" || cnf.BackupClient.EnableBackupClient == "auto" {
				cnf.BackupClient.EnableBackupClient = "no"
			}
		}
	} else {
		log.Warnf("get instance info from common_config failed: %v", err)
	}
	// 默认启用备份客户端，只有明确是 no 才不上传备份
	if cnf.BackupClient.EnableBackupClient == "" || cnf.BackupClient.EnableBackupClient == "auto" {
		cnf.BackupClient.EnableBackupClient = "yes"
	}
	// 如果本机是 master 且设置了 master 限速，则覆盖默认限速
	if cnf.Public.IOLimitMasterFactor > 0.0001 && cnf.Public.MysqlRole == cst.RoleMaster {
		cnf.Public.IOLimitMBPerSec = int(math.Max(10,
			cnf.Public.IOLimitMasterFactor*float64(cnf.Public.IOLimitMBPerSec)))
		cnf.PhysicalBackup.Throttle = int(math.Max(1,
			cnf.Public.IOLimitMasterFactor*float64(cnf.PhysicalBackup.Throttle)))
	}
	if cnf.LogicalBackup.TrxConsistencyOnly == nil {
		cnf.LogicalBackup.TrxConsistencyOnly = &config.TruePtr
	}
	return nil
}
