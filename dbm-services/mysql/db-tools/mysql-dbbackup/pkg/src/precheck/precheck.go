// Package precheck TODO
package precheck

import (
	"database/sql"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// BeforeDump precheck before dumping backup
// 检查备份方式
// 检查是否可连接
// 检查字符集
// 删除就备份
// 检查磁盘空间
func BeforeDump(cnf *config.BackupConfig) error {
	dbh, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return err
	}
	defer func() {
		_ = dbh.Close()
	}()
	/*
		if err := CheckBackupType(cnf); err != nil {
			return err
		}
	*/
	cnfPublic := &cnf.Public

	/*
		// check myisam tables
		if err = CheckEngineTables(cnf, dbh); err != nil {
			return err
		}
	*/
	// check server charset
	if err := CheckCharset(cnfPublic, dbh); err != nil {
		logger.Log.Errorf("failed to get Mysqlcharset for %d", cnfPublic.MysqlPort)
		return err
	}

	// 例行删除旧备份
	logger.Log.Infof("remove old backup files OldFileLeftDay=%d normally", cnfPublic.OldFileLeftDay)
	if err := DeleteOldBackup(cnfPublic, cnfPublic.OldFileLeftDay); err != nil {
		logger.Log.Warn("failed to delete old backup, err:", err)
	}

	if cnf.Public.IfBackupData() {
		if err := CheckAndCleanDiskSpace(cnfPublic, dbh); err != nil {
			logger.Log.Errorf("disk space is not enough for %d, err:%s", cnfPublic.MysqlPort, err.Error())
			return err
		}
	}

	return nil
}

// CheckBackupType check and fix backup type
func CheckBackupType(cnf *config.BackupConfig, engine string) error {
	backupSize, err := util.CalServerDataSize(cnf.Public.MysqlPort)
	if err != nil {
		return err
	}
	if cnf.Public.BackupType == cst.BackupTypeAuto {
		if engine == cst.StorageEngineTokudb || engine == cst.StorageEngineRocksdb {
			logger.Log.Infof("BackupType auto with engine=%s, use physical", engine)
			cnf.Public.BackupType = cst.BackupPhysical
			return nil
		}
		// report 时需要用真实的 backup type
		if backupSize > cst.BackupTypeAutoDataSizeGB*1024*1024*1024 {
			logger.Log.Infof("data size %d for port %d is larger than %d GB, use physical",
				backupSize, cnf.Public.MysqlPort, cst.BackupTypeAutoDataSizeGB)
			cnf.Public.BackupType = cst.BackupPhysical
		} else {
			cnf.Public.BackupType = cst.BackupLogical
		}
		if glibcVer, err := util.GetGlibcVersion(); err != nil {
			logger.Log.Warn("failed to glibc version, err:", err)
		} else if glibcVer < "2.14" {
			// mydumper need glibc version >= 2.14
			logger.Log.Infof("BackupType auto with glibc version %s < 2.14, use physical", glibcVer)
			cnf.Public.BackupType = cst.BackupPhysical
		}
	}
	return nil
}

// CheckEngineTables 只有在 master 上进行物理备份数据时，才执行检查
func CheckEngineTables(cnf *config.BackupConfig, db *sql.DB) error {
	if !(cnf.Public.BackupType == cst.BackupPhysical &&
		cnf.Public.MysqlRole == cst.RoleMaster &&
		cnf.Public.IfBackupData()) {
		return nil
	}
	testMysiamNum, err := mysqlconn.TestEngineTablesNum("MyISAM", cnf.PhysicalBackup.MaxMyisamTables, db)
	if err != nil {
		return err
	}
	if testMysiamNum {
		return errors.Errorf("instance %d has mysiam tables count > %d (PhysicalBackup.MaxMyisamTables)",
			cnf.Public.MysqlPort, cnf.PhysicalBackup.MaxMyisamTables)
	}
	return nil
}

func CheckEngineTablesFromMonitorReg() {
	//regPath := "/home/mysql/mysql-monitor/table-engine-count-${PORT}.reg"
}
