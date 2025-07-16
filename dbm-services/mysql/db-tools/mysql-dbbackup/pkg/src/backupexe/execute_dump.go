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
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
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
	logBinDisabled := false
	if logBinStr, err := mysqlconn.GetSingleGlobalVar("log_bin", db); err == nil {
		if logBin, err := cmutil.ToBoolExtE(logBinStr); err == nil {
			logBinDisabled = !logBin
		}
	}
	mysqlVersion, isOfficial := util.VersionParser(versionStr)
	XbcryptBin = GetXbcryptBin(mysqlVersion, isOfficial)

	metaInfo := &dbareport.IndexContent{}
	dumper, err := BuildDumper(cnf, metaInfo, db) // 会在里面确定备份方式
	if err != nil {
		return nil, err
	}
	if err := dumper.initConfig(versionStr, logBinDisabled); err != nil {
		return nil, err
	}
	if cnf.BackupToRemote.EnableRemote && cnf.Public.BackupType != cst.BackupPhysical {
		return nil, errors.Errorf("backup stream to remote only support physical but got %s for port=%d",
			cnf.Public.BackupType, cnf.Public.MysqlPort)
	}
	if cnf.BackupToRemote.EnableRemote && !cnf.Public.IfBackupData() {
		logger.Log.Warnf("backup-to-remote=true only works with DataSchemaGrant include data. set EnableRemote=false")
		cnf.BackupToRemote.EnableRemote = false
	}
	// BuildDumper 里面会修正备份方式，所以 SetEnv 要放在后面执行
	if envErr := SetEnv(cnf.Public.BackupType, versionStr); envErr != nil {
		return nil, envErr
	}

	// needn't set timeout for slave
	if err = dumper.Execute(ctx); err != nil {
		return nil, err
	}
	if err = dumper.PrepareBackupMetaInfo(cnf, metaInfo); err != nil {
		return nil, err
	}
	// 如果是 slave 节点，提前获取他的 master_host, master_port
	if lo.Contains([]string{cst.RoleSlave, cst.RoleRepeater}, strings.ToLower(cnf.Public.MysqlRole)) {
		masterHost, masterPort, err := mysqlconn.ShowMysqlSlaveStatus(db)
		if err != nil {
			return nil, err
		}
		if metaInfo.BinlogInfo.ShowSlaveStatus == nil {
			metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{}
		}
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = masterHost
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = masterPort
	}

	if err = buildMetaInfo(cnf, metaInfo); err != nil {
		return nil, err
	}
	metaInfo.BackupTool = BackupTool
	return metaInfo, nil
}

func buildMetaInfo(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error {
	cnfPub := &cnf.Public
	db, err := mysqlconn.InitConn(cnfPub)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	versionStr, err := mysqlconn.GetMysqlVersion(db)
	if err != nil {
		return err
	}
	metaInfo.MysqlVersion = versionStr
	storageEngineStr, err := mysqlconn.GetStorageEngine(db)
	if err != nil {
		return err
	}
	binlogFormat, rowImage := mysqlconn.GetBinlogFormat(db)
	sqlMode, _ := mysqlconn.GetSingleGlobalVar("sql_mode", db)

	metaInfo.BackupType = cnfPub.BackupType
	metaInfo.BackupHost = cnfPub.MysqlHost
	metaInfo.BackupPort = cnfPub.MysqlPort
	metaInfo.MysqlRole = cnfPub.MysqlRole
	metaInfo.DataSchemaGrant = cnfPub.DataSchemaGrant
	metaInfo.BillId = cnfPub.BillId
	metaInfo.ClusterId = cnfPub.ClusterId
	metaInfo.ClusterAddress = cnfPub.ClusterAddress
	metaInfo.ShardValue = cnfPub.ShardValue
	metaInfo.BkBizId = cnfPub.BkBizId
	metaInfo.BkCloudId = cnfPub.BkCloudId
	metaInfo.BackupCharset = cnfPub.MysqlCharset
	metaInfo.StorageEngine = storageEngineStr
	metaInfo.BinlogFormat = binlogFormat
	metaInfo.BinlogRowImage = rowImage
	metaInfo.SqlMode = sqlMode
	metaInfo.TimeZone, _ = time.Now().Zone()
	metaInfo.ConsistentBackupTime = metaInfo.BackupConsistentTime
	// BeginTime, EndTime, ConsistentTime, BinlogInfo,storageEngineStr build in PrepareBackupMetaInfo

	metaInfo.BackupId = cnfPub.BackupId
	metaInfo.EncryptEnable = cnfPub.EncryptOpt.EncryptEnable
	metaInfo.FileRetentionTag = cnf.BackupClient.FileTag
	return nil
}
