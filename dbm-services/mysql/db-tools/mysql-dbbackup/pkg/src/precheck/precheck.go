// Package precheck TODO
package precheck

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
)

// PrecheckBeforeDump precheck before dumping backup
func PrecheckBeforeDump(cnfPublic *parsecnf.CnfShared) error {
	// check server charset
	if err := CheckCharset(cnfPublic); err != nil {
		logger.Log.Error("failed to get Mysqlcharset")
		return err
	}

	// check disk space
	if err := DeleteOldBackup(cnfPublic, cnfPublic.OldFileLeftDay); err != nil {
		logger.Log.Error("failed to delete old backup, err:", err)
		return err
	}

	if err := EnableBackup(cnfPublic); err != nil {
		logger.Log.Error("disk space is not enough, err:", err)
		return err
	}
	return nil
}
