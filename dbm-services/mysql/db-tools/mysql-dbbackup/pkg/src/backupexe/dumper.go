// Package backupexe TODO
package backupexe

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
)

// Dumper TODO
type Dumper interface {
	initConfig() error
	Execute(enableTimeOut bool) error
}

// BuildDumper TODO
func BuildDumper(cnf *parsecnf.Cnf) (dumper Dumper, err error) {
	if strings.ToLower(cnf.Public.BackupType) == "logical" {
		if err := validate.GoValidateStruct(cnf.LogicalBackup); err != nil {
			return nil, err
		}
		dumper = &LogicalDumper{
			cnf: cnf,
		}
	} else if strings.ToLower(cnf.Public.BackupType) == "physical" {
		if err := validate.GoValidateStruct(cnf.PhysicalBackup); err != nil {
			return nil, err
		}

		dumper = &PhysicalDumper{
			cnf: cnf,
		}
	} else {
		logger.Log.Error(fmt.Sprintf("Unknown BackupType: %s", cnf.Public.BackupType))
		err := fmt.Errorf("unknown BackupType: %s", cnf.Public.BackupType)
		return nil, err
	}

	return dumper, nil
}
