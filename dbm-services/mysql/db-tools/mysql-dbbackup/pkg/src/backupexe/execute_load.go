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

	if pathNum >= 2 {
		err := errors.New("Setting multiple IndexFilePath values is not allowed")
		return err
	}

	var indexPath string
	if cnf.LogicalLoad.IndexFilePath != "" {
		indexPath = cnf.LogicalLoad.IndexFilePath
	} else if cnf.PhysicalLoad.IndexFilePath != "" {
		indexPath = cnf.PhysicalLoad.IndexFilePath
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

	loader, err := BuildLoader(cnf, indexFileContent.BackupType, indexFileContent.BackupTool)
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
