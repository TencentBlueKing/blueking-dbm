// Package backupexe TODO
package backupexe

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/precheck"
)

// Dumper TODO
type Dumper interface {
	initConfig(mysqlVersion string) error
	Execute(ctx context.Context) error
	PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error)
}

// BuildDumper return logical or physical dumper
func BuildDumper(cnf *config.BackupConfig, db *sql.DB) (dumper Dumper, err error) {
	if cnf.Public.IfBackupGrantOnly() {
		logger.Log.Infof("only backup grants for %d", cnf.Public.MysqlPort)
		cnf.Public.BackupType = cst.BackupLogical
		dumper = &DumperGrant{
			cnf: cnf,
		}
		return dumper, nil
	}
	storageEngine, err := mysqlconn.GetStorageEngine(db)
	if err != nil {
		return nil, err
	}
	if err = precheck.CheckBackupType(cnf, storageEngine); err != nil {
		return nil, err
	}

	if strings.ToLower(cnf.Public.BackupType) == cst.BackupLogical {
		if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpAuto || cnf.LogicalBackup.UseMysqldump == "" {
			if glibcVer, err := cmutil.GetGlibcVersion(); err != nil {
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
			if err := validate.GoValidateStruct(cnf.LogicalBackup, false); err != nil {
				return nil, err
			}
			dumper = &LogicalDumper{
				cnf: cnf,
			}
		} else if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpYes {
			if err := validate.GoValidateStruct(cnf.LogicalBackupMysqldump, false); err != nil {
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
		if err := validate.GoValidateStruct(cnf.PhysicalBackup, false); err != nil {
			return nil, err
		}

		if cst.StorageEngineRocksdb == storageEngine {
			dumper = &PhysicalRocksdbDumper{
				cfg: cnf,
			}
		} else if storageEngine == cst.StorageEngineTokudb {
			dumper = &PhysicalTokudbDumper{
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
