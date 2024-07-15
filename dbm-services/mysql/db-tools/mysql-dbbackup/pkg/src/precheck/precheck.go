// Package precheck TODO
package precheck

import (
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
	if err := CheckBackupType(cnf); err != nil {
		return err
	}
	cnfPublic := &cnf.Public

	dbh, err := mysqlconn.InitConn(cnfPublic)
	if err != nil {
		return err
	}
	defer func() {
		_ = dbh.Close()
	}()

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

	if err := CheckAndCleanDiskSpace(cnfPublic, dbh); err != nil {
		logger.Log.Errorf("disk space is not enough for %d, err:%s", cnfPublic.MysqlPort, err.Error())
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
