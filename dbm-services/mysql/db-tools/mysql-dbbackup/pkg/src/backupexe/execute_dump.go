// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package backupexe

import (
	"context"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// ExecuteBackup execute dump backup command
func ExecuteBackup(ctx context.Context, cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	// get mysql version from mysql server, and then set env variables
	db, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = db.Close()
	}()
	versionStr, err := mysqlconn.GetMysqlVersion(db)
	if err != nil {
		return nil, err
	}

	mysqlVersion, isOfficial := util.VersionParser(versionStr)
	XbcryptBin = GetXbcryptBin(mysqlVersion, isOfficial)

	dumper, err := BuildDumper(cnf, db) // 会在里面确定备份方式
	if err != nil {
		return nil, err
	}
	if err := dumper.initConfig(versionStr); err != nil {
		return nil, err
	}

	// BuildDumper 里面会修正备份方式，所以 SetEnv 要放在后面执行
	if envErr := SetEnv(cnf.Public.BackupType, versionStr); envErr != nil {
		return nil, envErr
	}

	// needn't set timeout for slave
	if err = dumper.Execute(ctx); err != nil {
		return nil, err
	}

	metaInfo, err := dumper.PrepareBackupMetaInfo(cnf)
	if err != nil {
		return nil, err
	}

	metaInfo.BackupTool = BackupTool
	return metaInfo, nil
}
