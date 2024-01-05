// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package dbareport

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/google/uuid"
	"github.com/mohae/deepcopy"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// BackupLogReport the reported dump file
type BackupLogReport struct {
	BackupMetaFileBase
	ExtraFields

	// EncryptedKey 如果备份加密，上报加密 key。加密短语 key 会通过 rsa 加密成密文 再上报
	EncryptedKey string `json:"encrypted_key"`

	FileName string `json:"file_name"`
	FileSize int64  `json:"file_size"`
	// FileType tar priv index other
	FileType string `json:"file_type"`
	// TaskId backup task_id
	TaskId string `json:"task_id"`

	cfg *config.BackupConfig
}

// BinlogStatusInfo master status and slave status
type BinlogStatusInfo struct {
	// ShowMasterStatus 当前实例 show master status 输出，本机位点
	ShowMasterStatus *StatusInfo `json:"show_master_status"`
	// ShowSlaveStatus 显示的是当前实例的 master 的位点
	ShowSlaveStatus *StatusInfo `json:"show_slave_status"`
}

// StatusInfo detailed binlog information
type StatusInfo struct {
	BinlogFile string `json:"binlog_file"`
	BinlogPos  string `json:"binlog_pos"`
	Gtid       string `json:"gtid"`
	MasterHost string `json:"master_host"`
	MasterPort int    `json:"master_port"`
}

// String 用于打印
func (s *StatusInfo) String() string {
	return fmt.Sprintf("Status{BinlogFile:%s, BinlogPos:%s, MasterHost:%s, MasterPort:%d}",
		s.BinlogFile, s.BinlogPos, s.MasterHost, s.MasterPort)
}

// String 用于打印
func (s *BinlogStatusInfo) String() string {
	return fmt.Sprintf("BinlogStatusInfo{MasterStatus:%+v, SlaveStatus:%+v}", s.ShowMasterStatus, s.ShowSlaveStatus)
}

// GenerateUUid Generate UUid
func GenerateUUid() (string, error) {
	uuids, err := uuid.NewUUID()
	if err != nil {
		logger.Log.Error("failed to generate Uuid, err: ", err)
		return "", err
	}
	return uuids.String(), nil
}

// GetFileType get the type of backup file
func GetFileType(fileName string) (fileType string) {
	if strings.HasSuffix(fileName, ".tar") {
		fileType = "tar"
	} else if strings.HasSuffix(fileName, ".priv") {
		fileType = "priv"
	} else if strings.HasSuffix(fileName, ".index") {
		fileType = "index"
	} else {
		fileType = "other"
	}
	return fileType
}

// NewBackupLogReport 备份开始前准备好必要的 BackupLogReport 信息
// 如果需要，生成 backup uuid
func NewBackupLogReport(cfg *config.BackupConfig) (logReport *BackupLogReport, err error) {
	logReport = &BackupLogReport{
		cfg: cfg,
	}
	if cfg.Public.BackupId != "" {
		logReport.BackupId = cfg.Public.BackupId
	} else {
		logReport.BackupId, err = GenerateUUid()
		if err != nil {
			return nil, err
		}
	}
	if cfg.Public.EncryptOpt.EncryptEnable {
		if ekey := cfg.Public.EncryptOpt.GetEncryptedKey(); len(ekey) <= 32 {
			logger.Log.Warnf("Not safe because EncryptPublicKey is not set, key=%s", ekey)
			logReport.EncryptedKey = ekey
		} else {
			logger.Log.Infof("Passphrase encrypted=%s passphrase=%s", ekey, cfg.Public.EncryptOpt.GetPassphrase())
			logReport.EncryptedKey = ekey
		}
	}
	return logReport, nil
}

// ReportCnf Report cfg info, 未启用
func (r *BackupLogReport) ReportCnf() error {
	cnfJson, err := json.Marshal(r.cfg)
	if err != nil {
		logger.Log.Error("Failed to marshal json encoding data from cfg, err: ", err)
		return err
	}
	reportFileName := fmt.Sprintf("dbareport_cnf_%d.log", r.cfg.Public.MysqlPort)

	reportFileName = filepath.Join(cst.DBAReportBase, reportFileName)
	reportFile, err := os.OpenFile(reportFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}
	defer func() {
		_ = reportFile.Close()
	}()

	_, err = reportFile.Write(cnfJson)
	if err != nil {
		logger.Log.Error("Failed to write json encoding data into cnf file, err: ", err)
		return err
	}
	_, err = reportFile.WriteString("\n")
	if err != nil {
		logger.Log.Error("Failed to write new line, err: ", err)
		return err
	}

	return nil
}

// ReportBackupStatus Report BackupStatus info
func (r *BackupLogReport) ReportBackupStatus(status string) error {
	var nBackupStatus BackupStatus
	nBackupStatus.BackupId = r.BackupId
	nBackupStatus.Status = status
	nBackupStatus.BillId = r.cfg.Public.BillId
	nBackupStatus.ClusterId = r.cfg.Public.ClusterId
	currentTime := time.Now().Format("2006-01-02 15:04:05")
	nBackupStatus.ReportTime = currentTime

	statusJson, err := json.Marshal(nBackupStatus)
	if err != nil {
		logger.Log.Error("Failed to marshal json encoding data from status, err: ", err)
		return err
	}
	statusFileName := fmt.Sprintf("dbareport_status_%d.log", r.cfg.Public.MysqlPort)

	if !cmutil.IsDirectory(r.cfg.Public.StatusReportPath) {
		if err := os.MkdirAll(r.cfg.Public.StatusReportPath, 0755); err != nil {
			logger.Log.Errorf("fail to mkdir: %s", r.cfg.Public.StatusReportPath)
		}
	}
	statusFileName = filepath.Join(r.cfg.Public.StatusReportPath, statusFileName)
	statusFile, err := os.OpenFile(statusFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}
	defer func() {
		_ = statusFile.Close()
	}()

	_, err = statusFile.Write(statusJson)
	if err != nil {
		logger.Log.Error("Failed to write json encoding data into status file, err: ", err)
		return err
	}
	_, err = statusFile.WriteString("\n")
	if err != nil {
		logger.Log.Error("Failed to write new line, err: ", err)
		return err
	}

	return nil
}

// ExecuteBackupClient execute backup_client which sends files to backup system
func (r *BackupLogReport) ExecuteBackupClient(fileName string) (taskid string, err error) {
	if r.cfg.BackupClient.Enable {
		backupClient, err := backupclient.New(
			r.cfg.BackupClient.BackupClientBin,
			"",
			r.cfg.BackupClient.FileTag,
			r.cfg.BackupClient.StorageType,
		)
		if err != nil {
			return "", err
		}
		logger.Log.Infof("upload register file %s", fileName)
		taskid, err = backupClient.Upload(fileName)
		logger.Log.Infof("upload register file %s with taskid=%s, err=%v", fileName, taskid, err)
		if err != nil {
			return "", err
		}
	} else {
		taskid = "-1"
		logger.Log.Infof("backup_client is not enabled: %s taskid=%s", fileName, taskid)
	}
	return taskid, nil
}

// ReportToLocalBackup 写入本地 infodba_schema.local_backup_report 表
// indexFilePath 是全路径
// 内存是传进来的，不是内部读取 indexFilePath
func (r *BackupLogReport) ReportToLocalBackup(indexFilePath string, metaInfo *IndexContent) error {
	logger.Log.Infof("write backup result to local_backup_report")
	db, err := mysqlconn.InitConn(&r.cfg.Public)
	if err != nil {
		return errors.WithMessage(err, "ReportBackupResult to db")
	}
	defer func() {
		_ = db.Close()
	}()
	isTspider, isTdbctl, err := mysqlconn.IsSpiderNode(db)
	if err != nil {
		return err
	}
	// 因为可能会改变 session 变量，所以那单独的连接处理
	conn, err := db.Conn(context.Background())
	if err != nil {
		return err
	}
	defer conn.Close()
	ctx := context.Background()
	if isTspider {
		if _, err = conn.ExecContext(ctx, "set session ddl_execute_by_ctl=OFF;"); err != nil {
			return err
		}
	} else if isTdbctl {
		if _, err = conn.ExecContext(ctx, "set session tc_admin=0"); err != nil {
			return err
		}
	}
	row := conn.QueryRowContext(ctx, "select @@server_id")
	if err != nil {
		return err
	}
	var serverId string
	if err = row.Scan(&serverId); err != nil {
		return err
	}
	// 写入本地db的file_list字段，精简一下
	fileList := make([]*TarFileItem, 0)
	for _, tf := range metaInfo.FileList {
		fileList = append(fileList, &TarFileItem{
			FileName: tf.FileName, FileSize: tf.FileSize, FileType: tf.FileType, TaskId: tf.TaskId})
	}
	fileListRaw, _ := json.Marshal(fileList)

	binlogInfo, _ := json.Marshal(metaInfo.BinlogInfo)
	extraFields, _ := json.Marshal(metaInfo.ExtraFields)
	sqlBuilder := sq.Replace(ModelBackupReport{}.TableName()).Columns("backup_id", "backup_type", "cluster_id",
		"cluster_address", "backup_host", "backup_port", "server_id", "mysql_role", "shard_value",
		"bill_id", "bk_biz_id", "mysql_version", "data_schema_grant", "is_full_backup",
		"backup_begin_time", "backup_end_time", "backup_consistent_time",
		"backup_meta_file",
		"binlog_info", "extra_fields",
		"file_list", "backup_config_file", "backup_status").Values(
		metaInfo.BackupId,
		metaInfo.BackupType,
		metaInfo.ClusterId,
		metaInfo.ClusterAddress,
		metaInfo.BackupHost,
		metaInfo.BackupPort,
		serverId,
		metaInfo.MysqlRole,
		metaInfo.ShardValue,
		metaInfo.BillId,
		metaInfo.BkBizId,
		metaInfo.MysqlVersion,
		metaInfo.DataSchemaGrant,
		metaInfo.IsFullBackup,
		metaInfo.BackupBeginTime, metaInfo.BackupEndTime, metaInfo.BackupConsistentTime,
		indexFilePath,
		binlogInfo, extraFields,
		fileListRaw, "", "")

	//_, err = sqlBuilder.RunWith(conn).Exec()
	sqlStr, sqlArgs, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	_, _ = conn.ExecContext(ctx, "set session sql_log_bin=0;") // 关闭 binlog
	_, err = conn.ExecContext(ctx, sqlStr, sqlArgs...)
	if err != nil {
		logger.Log.Warnf("failed to write %d local_backup_report, err: %s, fix it", metaInfo.BackupPort, err)
		if err = migrateLocalBackupSchema(err, conn); err != nil {
			return err
		}
		_, err = conn.ExecContext(ctx, sqlStr, sqlArgs...)
		if err != nil {
			return errors.Wrap(err, "write local_backup_report again")
		}
	}
	return nil
}

// ReportBackupResult Report BackupLogReport info
// run ExecuteBackupClient to upload to remote
// report backup to db
// report backup to log file
func (r *BackupLogReport) ReportBackupResult(indexFilePath string, index, upload bool) error {
	var err error
	var metaInfo = &IndexContent{}
	if buf, err := os.ReadFile(indexFilePath); err != nil {
		return err
	} else {
		if err = json.Unmarshal(buf, metaInfo); err != nil {
			return errors.WithMessagef(err, "unmarshal metaInfo %s", indexFilePath)
		}
	}
	if index {
		// index file 里面不会包含自身信息，这里上报时添加
		metaInfo.AddIndexFileItem(indexFilePath)
	}

	if upload {
		// 上传、上报备份文件
		for _, f := range metaInfo.FileList {
			filePath := filepath.Join(r.cfg.Public.BackupDir, f.FileName)
			var taskId string
			if taskId, err = r.ExecuteBackupClient(filePath); err != nil {
				return err
			}
			f.TaskId = taskId
			backupTaskResult := BackupLogReport{}
			backupTaskResult.BackupMetaFileBase = deepcopy.Copy(metaInfo.BackupMetaFileBase).(BackupMetaFileBase)
			backupTaskResult.ExtraFields = deepcopy.Copy(metaInfo.ExtraFields).(ExtraFields)
			backupTaskResult.EncryptedKey = r.EncryptedKey
			backupTaskResult.ConsistentBackupTime = metaInfo.BackupConsistentTime
			backupTaskResult.TaskId = taskId
			backupTaskResult.FileName = f.FileName
			backupTaskResult.FileType = f.FileType
			backupTaskResult.FileSize = f.FileSize
			Report().Files.Println(backupTaskResult)
		}
	}

	// report backup record
	//  index file 里面是完整的信息，上报日志以及写 local_backup_report，无需包含文件包含内容
	fileListSimple := make([]*TarFileItem, 0)
	for _, tf := range metaInfo.FileList {
		fileListSimple = append(fileListSimple, &TarFileItem{
			FileName: tf.FileName, FileSize: tf.FileSize, FileType: tf.FileType, TaskId: tf.TaskId})
	}
	metaInfo.FileList = fileListSimple
	Report().Result.Println(metaInfo)

	if err = r.ReportToLocalBackup(indexFilePath, metaInfo); err != nil {
		return err
	}
	return nil
}
