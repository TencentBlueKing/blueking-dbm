// Package backupexe TODO
package backupexe

import (
	"fmt"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/precheck"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// Dumper TODO
type Dumper interface {
	initConfig(mysqlVersion string) error
	Execute(enableTimeOut bool) error
	PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error)
}

// BuildDumper return logical or physical dumper
func BuildDumper(cnf *config.BackupConfig, storageEngine string) (dumper Dumper, err error) {
	if err = precheck.CheckBackupType(cnf); err != nil {
		return nil, err
	}
	if strings.ToLower(cnf.Public.BackupType) == cst.BackupLogical {
		if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpAuto || cnf.LogicalBackup.UseMysqldump == "" {
			if glibcVer, err := util.GetGlibcVersion(); err != nil {
				logger.Log.Warn("failed to glibc version, err:", err)
			} else if glibcVer < "2.14" {
				// mydumper need glibc version >= 2.14
				logger.Log.Infof("UseMysqldump auto with glibc version %s < 2.14, use mysqldump", glibcVer)
				cnf.LogicalBackup.UseMysqldump = cst.LogicalMysqldumpYes
			} else {
				logger.Log.Infof("UseMysqldump auto with glibc version %s >= 2.14, use mydumper", glibcVer)
				cnf.LogicalBackup.UseMysqldump = cst.LogicalMysqldumpNo
			}
		}
		if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpNo {
			if err := validate.GoValidateStruct(cnf.LogicalBackup, false, false); err != nil {
				return nil, err
			}
			dumper = &LogicalDumper{
				cnf: cnf,
			}
		} else if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpYes {
			if err := validate.GoValidateStruct(cnf.LogicalBackupMysqldump, false, false); err != nil {
				return nil, err
			}
			dumper = &LogicalDumperMysqldump{
				cnf: cnf,
			}
		} else {
			return nil, errors.Errorf("unknown LogicalBackup.UseMysqldump %s", cnf.LogicalBackup.UseMysqldump)
		}

		if err := cnf.LogicalBackup.ValidateFilter(); err != nil {
			return nil, err
		}
	} else if strings.ToLower(cnf.Public.BackupType) == cst.BackupPhysical {
		if err := validate.GoValidateStruct(cnf.PhysicalBackup, false, false); err != nil {
			return nil, err
		}

		if cst.StorageEngineRocksdb == storageEngine {
			dumper = &PhysicalRocksdbDumper{
				cfg: cnf,
			}
		} else {
			dumper = &PhysicalDumper{
				cnf: cnf,
			}
		}
	} else {
		logger.Log.Error(fmt.Sprintf("Unknown BackupType: %s", cnf.Public.BackupType))
		err := fmt.Errorf("unknown BackupType: %s", cnf.Public.BackupType)
		return nil, err
	}

	return dumper, nil
}
