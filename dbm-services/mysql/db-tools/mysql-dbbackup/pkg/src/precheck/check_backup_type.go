package precheck

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// CheckBackupType check and fix backup type
func CheckBackupType(cnf *config.BackupConfig, storageEngine string) error {
	backupSize, err := util.CalServerDataSize(cnf.Public.MysqlPort)
	if err != nil {
		return err
	}
	if cnf.Public.BackupType == cst.BackupTypeAuto {
		if storageEngine == cst.StorageEngineTokudb || storageEngine == cst.StorageEngineRocksdb {
			logger.Log.Infof("BackupType auto with engine=%s, use physical", storageEngine)
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
