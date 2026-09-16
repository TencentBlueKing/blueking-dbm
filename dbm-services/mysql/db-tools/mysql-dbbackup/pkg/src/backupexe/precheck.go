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
package backupexe

import (
	"context"
	"database/sql"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
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
func (r *BackupRunner) BeforeDump(ctx context.Context, cnf *config.BackupConfig) error {
	dbh, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return err
	}
	defer func() {
		_ = dbh.Close()
	}()
	r.storageEngine, err = mysqlconn.GetStorageEngine(dbh)
	if err != nil {
		return err
	}
	r.mysqlVersion, err = mysqlconn.GetMysqlVersion(dbh)
	if err != nil {
		return err
	}
	r.glibcVersion, err = cmutil.GetGlibcVersion()
	if err != nil {
		logger.Log.Warn("failed to glibc version, err:", err)
	}
	r.dataDirSize, err = util.CalServerDataSize(cnf.Public.MysqlPort)
	if err != nil {
		logger.Log.Warnf("failed to get datadir size for %d", cnf.Public.MysqlPort)
	}

	// 确定备份类型
	if err = r.CheckBackupType(cnf, r.storageEngine); err != nil {
		return err
	}
	// 之后，备份类型已经确定

	// check server charset, need correct charset
	if err = CheckCharset(cnf, r.mysqlVersion, dbh); err != nil {
		logger.Log.Errorf("failed to get Mysqlcharset for %d", cnf.Public.MysqlPort)
		return err
	}

	/*
		// check myisam tables
		if err = CheckEngineTables(cnf, dbh); err != nil {
			return err
		}
	*/
	cnfPublic := &cnf.Public
	// 例行删除旧备份
	logger.Log.Infof("remove old backup files OldFileLeftDay=%d normally", cnfPublic.OldFileLeftDay)
	_, err = DeleteOldBackup(cnfPublic, cnfPublic.OldFileLeftDay)
	if err != nil {
		logger.Log.Warn("failed to delete old backup, err:", err)
	}

	if cnf.Public.IfBackupData() || cnf.Public.BackupType == cst.BackupPhysical {
		if err := r.CheckAndCleanDiskSpace(cnf, dbh); err != nil {
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

// calPartialDatabasesSize 逻辑备份部分库时，通过 db_table_filter 解析出实际匹配的数据库列表，
// 然后计算这些数据库对应的 datadir 子目录大小之和
func calPartialDatabasesSize(cnf *config.BackupConfig, dbh *sql.DB) (uint64, error) {
	tf := &cnf.LogicalBackup.TableFilter
	var databases, excludeDatabases []string
	if tf.Databases == "" || tf.Databases == "*" {
		databases = []string{"*"}
	} else {
		databases = strings.Split(tf.Databases, ",")
	}
	if tf.ExcludeDatabases != "" {
		excludeDatabases = strings.Split(tf.ExcludeDatabases, ",")
	}
	filter, err := db_table_filter.NewFilter(databases, []string{"*"}, excludeDatabases, []string{})
	if err != nil {
		return 0, errors.WithMessage(err, "build db filter for partial backup")
	}
	dbNames, err := filter.GetDbsByConnRaw(dbh)
	if err != nil {
		return 0, errors.WithMessage(err, "get databases by filter")
	}
	if len(dbNames) == 0 {
		return 0, errors.New("no matching databases found for partial backup")
	}
	logger.Log.Infof("partial backup databases resolved: %v", dbNames)
	return util.CalDatabasesDirSize(cnf.Public.MysqlPort, dbNames)
}
