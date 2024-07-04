// Package precheck TODO
package precheck

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// BeforeDump precheck before dumping backup
func BeforeDump(cnf *config.BackupConfig) error {
	if err := CheckBackupType(cnf); err != nil {
		return err
	}

	cnfPublic := &cnf.Public
	// check server charset
	if err := CheckCharset(cnfPublic); err != nil {
		logger.Log.Error("failed to get Mysqlcharset")
		return err
	}

	// 例行删除旧备份
	if err := DeleteOldBackup(cnfPublic, cnfPublic.OldFileLeftDay); err != nil {
		logger.Log.Warn("failed to delete old backup, err:", err)
	}

	if err := CheckAndCleanDiskSpace(cnfPublic); err != nil {
		logger.Log.Error("disk space is not enough, err:", err)
		return err
	}
	return nil
}

// CheckBackupType check and fix backup type
func CheckBackupType(cnf *config.BackupConfig) error {
	backupSize, err := util.CalServerDataSize(cnf.Public.MysqlPort)
	if err != nil {
		return err
	}
	if cnf.Public.BackupType == cst.BackupTypeAuto {
		// report 时需要用真实的 backup type
		if backupSize > cst.BackupTypeAutoDataSizeGB*1024*1024*1024 {
			logger.Log.Info("data size %d for port %d is larger than %d GB, use physical",
				backupSize, cst.BackupTypeAutoDataSizeGB, cnf.Public.MysqlPort)
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
