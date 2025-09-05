/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package backupexe

import (
	"database/sql"
	"strings"

	"github.com/pkg/errors"
	"github.com/samber/lo"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// CheckCharset Check and fix mysql server charset
// might change the backup_type
func CheckCharset(cnf *config.BackupConfig, mysqlVersion string, dbh *sql.DB) error {
	confCharset := cnf.Public.MysqlCharset
	var superCharset string
	verStr, _ := util.VersionParser(mysqlVersion)
	if strings.Compare(verStr, "005005003") == -1 { // mysql_version <5.5.3
		superCharset = "utf8"
	} else {
		superCharset = "utf8mb4"
	}
	if !(cnf.Public.IfBackupData() && cnf.Public.BackupType == cst.BackupLogical) {
		if confCharset == "auto" || confCharset == "" {
			logger.Log.Info("use charset 'binary' for schema or physical backup")
			cnf.Public.MysqlCharset = "binary" // superCharset
		}
		return nil
	}

	// 备份数据，且未逻辑备份
	var goodCharset = []string{"latin1", "utf8", "utf8mb4"}
	if confCharset == "auto" || confCharset == "" {
		serverCharset, err := mysqlconn.GetAllMysqlCharset(true, true, true, true, dbh)
		if err != nil {
			logger.Log.Error("can't select mysql server charset , error :", err)
			return errors.WithMessagef(err, "failed to get charset from %d", cnf.Public.MysqlPort)
		}
		if len(serverCharset) == 2 &&
			lo.Contains(serverCharset, "utf8") && lo.Contains(serverCharset, "utf8mb4") {
			// "utf8", "utf8mb4" -> utf8mb4
			logger.Log.Infof("use charset 'utf8mb4' for %+v", serverCharset)
			superCharset = "utf8mb4"
		} else if len(serverCharset) >= 3 {
			logger.Log.Infof("use charset 'binary' for %+v", serverCharset)
			superCharset = "binary"
		} else if lo.Contains(goodCharset, serverCharset[0]) {
			logger.Log.Infof("use charset '%s' for good charset", serverCharset)
			superCharset = serverCharset[0]
		} else {
			logger.Log.Infof("use charset 'binary' for bad charset:%s", serverCharset)
			superCharset = "binary"
		}
		cnf.Public.MysqlCharset = superCharset
		return nil
	}
	logger.Log.Info("use character set:", cnf.Public.MysqlCharset, "  to backup")
	return nil
}
