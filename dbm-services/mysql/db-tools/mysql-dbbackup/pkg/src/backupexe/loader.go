package backupexe

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// Loader interface
type Loader interface {
	initConfig(indexContent *dbareport.IndexContent) error
	Execute() error
}

// BuildLoader TODO
func BuildLoader(cnf *config.BackupConfig, backupType string) (loader Loader, err error) {
	if strings.ToLower(backupType) == cst.BackupLogical {
		if err := validate.GoValidateStruct(cnf.LogicalLoad, false, false); err != nil {
			return nil, err
		}
		loader = &LogicalLoader{
			cnf: cnf,
		}
	} else if strings.ToLower(backupType) == cst.BackupPhysical {
		if err := validate.GoValidateStruct(cnf.PhysicalLoad, false, false); err != nil {
			return nil, err
		}
		loader = &PhysicalLoader{
			cnf: cnf,
		}
	} else {
		logger.Log.Error(fmt.Sprintf("Unknown BackupType: %s", backupType))
		err := fmt.Errorf("unknown BackupType: %s", backupType)
		return nil, err
	}

	return loader, nil
}
