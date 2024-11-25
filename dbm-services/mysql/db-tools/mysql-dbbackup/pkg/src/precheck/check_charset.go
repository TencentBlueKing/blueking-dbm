/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package precheck

import (
	"database/sql"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// CheckCharset Check and fix mysql server charset
func CheckCharset(cnf *config.BackupConfig, dbh *sql.DB) error {
	//if strings.ToLower(cnf.Public.BackupType) != cst.BackupLogical {
	//	return nil
	//}
	confCharset := cnf.Public.MysqlCharset
	var superCharset string

	version, verErr := mysqlconn.GetMysqlVersion(dbh)
	if verErr != nil {
		return verErr
	}
	verStr, _ := util.VersionParser(version)
	if strings.Compare(verStr, "005005003") == -1 { // mysql_version <5.5.3
		superCharset = "utf8"
	} else {
		superCharset = "utf8mb4"
	}

	if confCharset == "auto" || confCharset == "" {
		// 如果 cnf.MysqlCharset 为空，则自动读取 character_set_server
		serverCharset, err := mysqlconn.MysqlSingleColumnQuery("select @@character_set_server", dbh)
		if err != nil {
			logger.Log.Error("can't select mysql server charset , error :", err)
			return errors.WithMessagef(err, "failed to get character_set_server from %d", cnf.Public.MysqlPort)
		}
		cnf.Public.MysqlCharset = serverCharset[0]
		return nil
	}
	if confCharset != "binary" && confCharset != superCharset && strings.ToUpper(cnf.Public.DataSchemaGrant) == "ALL" {
		var goodCharset = []string{"latin1", "utf8", "utf8mb4"}

		serverCharset, err := mysqlconn.GetMysqlCharset(dbh)
		for i := 0; i < len(serverCharset); i++ {
			grep := false
			for j := 0; j < len(goodCharset); j++ {
				if serverCharset[i] == goodCharset[j] {
					grep = true
				}
			}
			if !grep {
				superCharset = "binary"
			}
		}

		if err != nil {
			logger.Log.Warn("get_server_data_charsets query failed,use super charset")
			cnf.Public.MysqlCharset = superCharset
		} else if len(serverCharset) > 1 {
			logger.Log.Warn("found multi character sets on server ")
			cnf.Public.MysqlCharset = superCharset
		} else if len(serverCharset) == 1 {
			cnf.Public.MysqlCharset = serverCharset[0]
			if serverCharset[0] != confCharset {
				logger.Log.Warn("backup config charset:'%s' and server charset '%s' are not the same."+
					" You should use %s to backup,please modify config charset to remove this warning",
					confCharset, serverCharset[0], serverCharset[0])
			}
		} else {
			tableNum := common.GetTableNum(cnf.Public.MysqlPort) // todo
			if tableNum > 1000 {
				cnf.Public.MysqlCharset = superCharset
				logger.Log.Warn("too much table, tableNum is %d,check server charset failed,"+
					"use super charset:%s to backup.", tableNum, superCharset)
			}
		}
	}
	logger.Log.Info("use character set:", cnf.Public.MysqlCharset, "  to backup")
	return nil
}
