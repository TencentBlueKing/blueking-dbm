package cmd

import (
	"fmt"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	// loadCmd
	loadCmd.PersistentFlags().StringVarP(&cnfFile, "config", "c", "",
		"one config file to load. logical backup need connect string given")

	// common load options for both logical and physical
	loadCmd.PersistentFlags().String("load-dir", "", "backup root path to save, overwrite LogicalLoad.MysqlLoadDir")
	loadCmd.PersistentFlags().StringP("load-index-file", "i", "",
		"backup index file, overwrite LogicalLoad.IndexFilePath, PhysicalLoad.IndexFilePath")
	loadCmd.PersistentFlags().Int("threads", 8, "threads for myloader or xtrabackup, "+
		"default os logic cores")
	viper.BindPFlag("LogicalLoad.MysqlLoadDir", loadCmd.PersistentFlags().Lookup("load-dir"))
	viper.BindPFlag("LogicalLoad.IndexFilePath", loadCmd.PersistentFlags().Lookup("load-index-file"))
	viper.BindPFlag("LogicalLoad.Threads", loadCmd.PersistentFlags().Lookup("threads"))
	viper.BindPFlag("PhysicalLoad.MysqlLoadDir", loadCmd.PersistentFlags().Lookup("load-dir"))
	viper.BindPFlag("PhysicalLoad.IndexFilePath", loadCmd.PersistentFlags().Lookup("load-index-file"))
	viper.BindPFlag("PhysicalLoad.Threads", loadCmd.PersistentFlags().Lookup("threads"))

	loadCmd.AddCommand(loadLogicalCmd)
	loadCmd.AddCommand(loadPhysicalCmd)
}

var loadCmd = &cobra.Command{
	Use:          "loadbackup",
	Short:        "Run load backup",
	Long:         `Run load backup using config, include logical and physical`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", cst.DbbackupGoInstallPath)
		}()
		cnf, err := initLoadCmd(cmd)
		if err != nil {
			return err
		}
		err = loadData(cnf, "")
		if err != nil {
			logger.Log.Error("Load Dbbackup: Failed. ", err.Error())
			return errors.WithMessage(err, "load data")
		}
		return nil
	},
}

func loadData(cnf *config.BackupConfig, backupType string) error {
	var indexPath string
	if backupType == "" { // auto  自动找 index file
		indexPath = cnf.LogicalLoad.IndexFilePath
		if indexPath == "" {
			indexPath = cnf.PhysicalLoad.IndexFilePath
		}
	} else if backupType == cst.BackupLogical {
		indexPath = cnf.LogicalLoad.IndexFilePath
	} else if backupType == cst.BackupPhysical {
		indexPath = cnf.PhysicalLoad.IndexFilePath
	} else {
		return errors.Errorf("unknown backupType %s for loader", backupType)
	}
	if indexPath == "" {
		return errors.Errorf("cannot find index file for backupType=%s", backupType)
	}

	metaInfo, err := backupexe.ParseJsonFile(indexPath)
	if err != nil {
		logger.Log.Errorf("can not parse index file:%s, errmsg:%s", indexPath, err)
		return err
	}
	if backupType != "" && metaInfo.BackupType != backupType {
		return errors.Errorf("BackupType not match, given [%s], but index file %s has [%s]",
			metaInfo.BackupType, indexPath, backupType)
	}

	exeErr := backupexe.ExecuteLoad(cnf, metaInfo)
	if exeErr != nil {
		return exeErr
	}
	logger.Log.Info("Load Success")
	return nil
}

func initLoadCmd(cmd *cobra.Command) (cnf *config.BackupConfig, err error) {
	configFile, _ := cmd.Flags().GetString("config") // loadbackup sub_command will call, so use Flags
	if configFile == "" {
		if err = viper.Unmarshal(&cnf); err != nil {
			return nil, errors.WithMessage(err, "parse params")
		}
	} else if configFile != "" {
		if err = cmutil.FileExistsErr(configFile); err != nil {
			return nil, err
		}
		if err = initConfig(configFile, &cnf); err != nil {
			return nil, errors.WithMessagef(err, "fail to parse %s", configFile)
		}
	}
	loadLogFile := fmt.Sprintf("dbloader_%d.log", viper.GetInt("LogicalLoad.MysqlPort"))
	if err = logger.InitLog(loadLogFile); err != nil {
		return nil, err
	}
	return cnf, nil
}
