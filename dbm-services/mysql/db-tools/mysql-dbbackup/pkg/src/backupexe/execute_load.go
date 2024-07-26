package backupexe

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
)

// ExecuteLoad execute load backup command
func ExecuteLoad(cnf *config.BackupConfig, indexFileContent *dbareport.IndexContent) error {
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
