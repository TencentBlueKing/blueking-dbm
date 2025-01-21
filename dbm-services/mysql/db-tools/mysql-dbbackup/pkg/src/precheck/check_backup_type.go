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
	"dbm-services/common/go-pubpkg/cmutil"
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
		if glibcVer, err := cmutil.GetGlibcVersion(); err != nil {
			logger.Log.Warn("failed to glibc version, err:", err)
		} else if glibcVer < "2.14" {
			// mydumper need glibc version >= 2.14
			logger.Log.Infof("BackupType auto with glibc version %s < 2.14, use physical", glibcVer)
			cnf.Public.BackupType = cst.BackupPhysical
		}
	}
	if cnf.Public.BackupType == cst.BackupPhysical && cnf.Public.IfBackupSchema() && !cnf.Public.IfBackupAll() {
		logger.Log.Warnf("BackupType physical cannot backup schema only, change it to logical")
		cnf.Public.BackupType = cst.BackupLogical
		cnf.LogicalBackup.UseMysqldump = cst.BackupTypeAuto
	}
	return nil
}
