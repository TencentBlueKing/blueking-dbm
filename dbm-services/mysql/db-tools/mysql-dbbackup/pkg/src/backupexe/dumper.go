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
)

// Dumper TODO
type Dumper interface {
	initConfig(mysqlVersion string, logBinDisabled bool) error
	Execute(ctx context.Context) error
	PrepareBackupMetaInfo(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error
}

// BuildDumper return logical or physical dumper
func (r *BackupRunner) BuildDumper(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent, db *sql.DB) (dumper Dumper, err error) {
	if cnf.Public.IfBackupGrantOnly() {
		logger.Log.Infof("only backup grants for %d. set backup-type to logical", cnf.Public.MysqlPort)
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
	/*
		if err = r.CheckBackupType(cnf, storageEngine); err != nil {
			return nil, err
		}
	*/
	if strings.EqualFold(cnf.Public.BackupType, cst.BackupLogical) {
		if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpAuto || cnf.LogicalBackup.UseMysqldump == "" {
			if r.glibcVersion != "" && r.glibcVersion < "2.14" {
				/*
					// mydumper need glibc version >= 2.14
					logger.Log.Infof("UseMysqldump auto with glibc version %s < 2.14, use mysqldump", glibcVer)
					cnf.LogicalBackup.UseMysqldump = cst.LogicalMysqldumpYes
				*/
				// 最新版本 mydumper 已经支持 glibc 2.14 以上版本
				cnf.LogicalBackup.UseMysqldump = cst.LogicalMysqldumpNo
			} else {
				logger.Log.Infof("UseMysqldump auto with glibc version %s >= 2.14, use mydumper", r.glibcVersion)
				cnf.LogicalBackup.UseMysqldump = cst.LogicalMysqldumpNo
			}
		}
		if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpNo {
			if err := validate.GoValidateStructTag(cnf.LogicalBackup, "ini"); err != nil {
				return nil, err
			}
			dumper = &LogicalDumper{
				cnf: cnf,
			}
		} else if cnf.LogicalBackup.UseMysqldump == cst.LogicalMysqldumpYes {
			if err := validate.GoValidateStructTag(cnf.LogicalBackupMysqldump, "ini"); err != nil {
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
	} else if strings.EqualFold(cnf.Public.BackupType, cst.BackupPhysical) {
		if err := validate.GoValidateStructTag(cnf.PhysicalBackup, "ini"); err != nil {
			return nil, err
		}
		if cmutil.MySQLVersionCompare(r.mysqlVersion, "8.0.0") >= 0 && r.glibcVersion < "2.14" {
			return nil, errors.Errorf("glibc version %s < 2.14, "+
				"not support physical backup for mysql 8.0.0+", r.glibcVersion)
		}
		if cst.StorageEngineRocksdb == storageEngine {
			dumper = &PhysicalRocksdbDumper{
				cnf: cnf,
			}
		} else if storageEngine == cst.StorageEngineTokudb {
			dumper = &PhysicalTokudbDumper{
				cnf: cnf,
			}
		} else {
			dumper = &PhysicalDumper{
				cnf:      cnf,
				metaInfo: metaInfo,
			}
		}
	} else {
		logger.Log.Error(fmt.Sprintf("Unknown BackupType: %s", cnf.Public.BackupType))
		err := fmt.Errorf("unknown BackupType: %s", cnf.Public.BackupType)
		return nil, err
	}

	return dumper, nil
}
