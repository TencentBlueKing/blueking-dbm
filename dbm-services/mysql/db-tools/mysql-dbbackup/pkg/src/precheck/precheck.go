// Package precheck TODO
package precheck

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// BeforeDump precheck before dumping backup
func BeforeDump(cnfPublic *config.Public) error {
	// check server charset
	if err := CheckCharset(cnfPublic); err != nil {
		logger.Log.Error("failed to get Mysqlcharset")
		return err
	}

	// 例行删除旧备份
	if err := DeleteOldBackup(cnfPublic, cnfPublic.OldFileLeftDay); err != nil {
		logger.Log.Warn("failed to delete old backup, err:", err)
	}

	if err := EnableBackup(cnfPublic); err != nil {
		logger.Log.Error("disk space is not enough, err:", err)
		return err
	}
	return nil
}
