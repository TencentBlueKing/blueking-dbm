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
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// CheckBackupType check and fix backup type
func (r *BackupRunner) CheckBackupType(cnf *config.BackupConfig, storageEngine string) (err error) {
	if cnf.Public.BackupType == cst.BackupTypeAuto {
		if strings.EqualFold(storageEngine, cst.StorageEngineTokudb) ||
			strings.EqualFold(storageEngine, cst.StorageEngineRocksdb) {
			logger.Log.Infof("BackupType auto with engine=%s, use physical", storageEngine)
			cnf.Public.BackupType = cst.BackupPhysical
			return nil
		}
		// report 时需要用真实的 backup type
		if r.dataDirSize > cst.BackupTypeAutoDataSizeGB*1024*1024*1024 {
			logger.Log.Infof("data size %d for port %d is larger than %d GB, use physical",
				r.dataDirSize, cnf.Public.MysqlPort, cst.BackupTypeAutoDataSizeGB)
			cnf.Public.BackupType = cst.BackupPhysical
		} else {
			cnf.Public.BackupType = cst.BackupLogical
		}
		if r.glibcVersion != "" && r.glibcVersion < "2.14" &&
			cmutil.MySQLVersionCompare(r.mysqlVersion, "8.0.0") >= 0 {
			// mysql 8.0 的物理备份，不支持 glibc < 2.14
			// 修复版本的 mydumper 已经支持 glibc < 2.14
			cnf.Public.BackupType = cst.BackupLogical
		}
	}
	if cnf.Public.IfBackupSchema() && !cnf.Public.IfBackupAll() {
		logger.Log.Warnf("BackupType physical cannot backup schema only, change it to logical")
		cnf.Public.BackupType = cst.BackupLogical
		cnf.LogicalBackup.UseMysqldump = cst.BackupTypeAuto
	}
	return nil
}
