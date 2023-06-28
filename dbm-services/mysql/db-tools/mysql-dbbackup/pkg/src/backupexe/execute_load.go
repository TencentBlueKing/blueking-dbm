package backupexe

import (
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// ExecuteLoad execute load backup command
func ExecuteLoad(cnf *config.BackupConfig) error {
	if cnf.LogicalLoad.IndexFilePath != "" && cnf.PhysicalLoad.IndexFilePath != "" {
		if cnf.LogicalLoad.IndexFilePath != cnf.PhysicalLoad.IndexFilePath {
			err := errors.New("the IndexFilePath of LogicalLoad should be same as " +
				"the IndexFilePath of PhysicalLoad, if you set both values")
			return err
		}
	}

	if envErr := SetEnv(); envErr != nil {
		return envErr
	}

	var indexPath string
	if cnf.LogicalLoad.IndexFilePath != "" {
		indexPath = cnf.LogicalLoad.IndexFilePath
	} else if cnf.PhysicalLoad.IndexFilePath != "" {
		indexPath = cnf.PhysicalLoad.IndexFilePath
	}

	indexFileContent, err := ParseJsonFile(indexPath)
	if err != nil {
		return err
	}

	loader, err := BuildLoader(cnf, indexFileContent.BackupType)
	if err != nil {
		return err
	}

	if err := loader.initConfig(indexFileContent); err != nil {
		return err
	}

	if err = loader.Execute(); err != nil {
		return err
	}
	return nil
}
