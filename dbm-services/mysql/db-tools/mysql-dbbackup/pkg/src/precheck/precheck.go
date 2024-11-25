/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package precheck TODO
package precheck

import (
	"database/sql"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
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
	storageEngine, err := mysqlconn.GetStorageEngine(dbh)
	if err != nil {
		return err
	}
	if err := CheckBackupType(cnf, storageEngine); err != nil {
		return err
	}
	cnfPublic := &cnf.Public

	/*
		// check myisam tables
		if err = CheckEngineTables(cnf, dbh); err != nil {
			return err
		}
	*/
	// check server charset, need correct charset
	if err := CheckCharset(cnf, dbh); err != nil {
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
