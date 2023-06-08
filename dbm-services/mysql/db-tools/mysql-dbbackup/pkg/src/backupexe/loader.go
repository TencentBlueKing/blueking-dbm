package backupexe

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
)

// Loader interface
type Loader interface {
	initConfig(indexContent *IndexContent) error
	Execute() error
}

// BuildLoader TODO
func BuildLoader(cnf *parsecnf.Cnf, backupType string) (loader Loader, err error) {
	if strings.ToLower(backupType) == "logical" {
		if err := validate.GoValidateStruct(cnf.LogicalLoad); err != nil {
			return nil, err
		}
		loader = &LogicalLoader{
			cnf: cnf,
		}
	} else if strings.ToLower(backupType) == "physical" {
		if err := validate.GoValidateStruct(cnf.PhysicalLoad); err != nil {
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
