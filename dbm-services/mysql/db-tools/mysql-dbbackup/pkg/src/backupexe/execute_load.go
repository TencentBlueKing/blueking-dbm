package backupexe

import (
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// ExecuteLoad execute load backup command
func ExecuteLoad(cnf *config.BackupConfig) error {
	pathNum := 0
	if cnf.LogicalLoad.IndexFilePath != "" {
		pathNum++
	}
	if cnf.PhysicalLoad.IndexFilePath != "" {
		pathNum++
	}
	if cnf.LogicalLoadMysqldump.IndexFilePath != "" {
		pathNum++
	}

	if pathNum >= 2 {
		err := errors.New("Setting multiple IndexFilePath values is not allowed")
		return err
	}

	var indexPath string
	useMysqldump := false
	if cnf.LogicalLoad.IndexFilePath != "" {
		indexPath = cnf.LogicalLoad.IndexFilePath
		useMysqldump = false
	} else if cnf.PhysicalLoad.IndexFilePath != "" {
		indexPath = cnf.PhysicalLoad.IndexFilePath
	} else if cnf.LogicalLoadMysqldump.IndexFilePath != "" {
		indexPath = cnf.LogicalLoadMysqldump.IndexFilePath
		useMysqldump = true
	}
	if indexPath == "" { // required
		return errors.New("loadbackup need IndexFilePath")
	}

	indexFileContent, err := ParseJsonFile(indexPath)
	if err != nil {
		return err
	}

	if envErr := SetEnv(indexFileContent.BackupType, indexFileContent.MysqlVersion); envErr != nil {
		return envErr
	}

	loader, err := BuildLoader(cnf, indexFileContent.BackupType, useMysqldump)
	if err != nil {
		return err
	}

	if err := loader.initConfig(indexFileContent); err != nil {
		return err
	}

	// 检查目标实例是否空闲

	if err = loader.Execute(); err != nil {
		return err
	}
	return nil
}
