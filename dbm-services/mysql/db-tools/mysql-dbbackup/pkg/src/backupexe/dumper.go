// Package backupexe TODO
package backupexe

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// Dumper TODO
type Dumper interface {
	initConfig(mysqlVersion string) error
	Execute(enableTimeOut bool) error
}

// BuildDumper return logical or physical dumper
func BuildDumper(cnf *config.BackupConfig) (dumper Dumper, err error) {
	if strings.ToLower(cnf.Public.BackupType) == "logical" {
		if err := validate.GoValidateStruct(cnf.LogicalBackup, false, false); err != nil {
			return nil, err
		}
		dumper = &LogicalDumper{
			cnf: cnf,
		}
	} else if strings.ToLower(cnf.Public.BackupType) == "physical" {
		if err := validate.GoValidateStruct(cnf.PhysicalBackup, false, false); err != nil {
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
