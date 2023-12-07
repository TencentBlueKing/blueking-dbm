package dbareport

import (
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
	ShowMasterStatus *StatusInfo `json:"show_master_status"`
	ShowSlaveStatus  *StatusInfo `json:"show_slave_status"`
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

func (r *BackupLogReport) ReportToLocalBackup(backupReport *IndexContent) error {
	logger.Log.Infof("write backup result to local_backup_report")
	db, err := mysqlconn.InitConn(&r.cfg.Public)
	if err != nil {
		return errors.WithMessage(err, "ReportBackupResult to db")
	}
	defer func() {
		_ = db.Close()
	}()
	binlogInfo, _ := json.Marshal(backupReport.BinlogInfo)
	filelist, _ := json.Marshal(backupReport.FileList)
	extraFileds, _ := json.Marshal(backupReport.ExtraFields)
	sqlBuilder := sq.Insert(ModelBackupReport{}.TableName()).Columns("backup_id", "backup_type", "cluster_id",
		"cluster_address", "backup_host", "backup_port", "mysql_role", "shard_value", "bill_id", "bk_biz_id",
		"mysql_version", "data_schema_grant", "is_full_backup",
		"backup_begin_time", "backup_end_time", "backup_consistent_time",
		"binlog_info", "file_list", "extra_fields",
		"backup_config_file", "backup_status").Values(
		backupReport.BackupId,
		backupReport.BackupType,
		backupReport.ClusterId,
		backupReport.ClusterAddress,
		backupReport.BackupHost,
		backupReport.BackupPort,
		backupReport.MysqlRole,
		backupReport.ShardValue,
		backupReport.BillId,
		backupReport.BkBizId,
		backupReport.MysqlVersion,
		backupReport.DataSchemaGrant,
		backupReport.IsFullBackup,
		backupReport.BackupBeginTime, backupReport.BackupEndTime, backupReport.BackupConsistentTime,
		binlogInfo, filelist, extraFileds,
		"", "")

	_, err = sqlBuilder.RunWith(db).Exec()
	if err != nil {
		logger.Log.Warn("failed to write local_backup_report, err:", err, ", try to fix it")
		if err = migrateLocalBackupSchema(err, false, db); err != nil {
			return err
		}
		_, err = sqlBuilder.RunWith(db).Exec()
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
func (r *BackupLogReport) ReportBackupResult(metaInfo *IndexContent) error {
	var err error
	// 上传、上报备份文件
	for _, f := range metaInfo.FileList {
		filePath := filepath.Join(r.cfg.Public.BackupDir, f.FileName)
		var taskId string
		if taskId, err = r.ExecuteBackupClient(filePath); err != nil {
			return err
		}
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
	// 上传并上报 meta index file
	// index file 里面不会包含自身信息
	indexFilePath := filepath.Join(r.cfg.Public.BackupDir, r.cfg.Public.TargetName()+".index")
	if taskId, err := r.ExecuteBackupClient(indexFilePath); err != nil {
		return err
	} else {
		backupTaskResult := BackupLogReport{}
		backupTaskResult.BackupMetaFileBase = deepcopy.Copy(metaInfo.BackupMetaFileBase).(BackupMetaFileBase)
		backupTaskResult.ExtraFields = deepcopy.Copy(metaInfo.ExtraFields).(ExtraFields)
		backupTaskResult.ConsistentBackupTime = metaInfo.BackupConsistentTime
		backupTaskResult.TaskId = taskId
		backupTaskResult.FileName = filepath.Base(indexFilePath)
		backupTaskResult.FileType = cst.FileIndex
		backupTaskResult.FileSize = cmutil.GetFileSize(indexFilePath)
		Report().Files.Println(backupTaskResult)
	}
	// report backup record
	Report().Result.Println(metaInfo)

	if err = r.ReportToLocalBackup(metaInfo); err != nil {
		return err
	}
	/*
		var backupResultArray []BackupLogReport
			dir, err := os.ReadDir(r.cfg.Public.BackupDir)
			if err != nil {
				logger.Log.Error("failed to read backupdir, err :", err)
				return err
			}
			for _, entry := range dir {
				if entry.IsDir() {
					continue
				}

				fileInfo, err := entry.Info()
				if err != nil {
					logger.Log.Error("failed to read file info: ", err)
					return err
				}
				// 这里也会把 .index 上报上去
				match := strings.HasPrefix(entry.Name(), r.cfg.Public.TargetName())
				if match {
					// execute backup_client, and send file to backup system
					var taskId string
					fileName := filepath.Join(r.cfg.Public.BackupDir, entry.Name())
					if taskId, err = r.ExecuteBackupClient(fileName); err != nil {
						return err
					}
					backupTaskResult := BackupLogReport{}
					backupTaskResult.BackupMetaFileBase = deepcopy.Copy(metaInfo.BackupMetaFileBase).(BackupMetaFileBase)
					backupTaskResult.ExtraFields = deepcopy.Copy(metaInfo.ExtraFields).(ExtraFields)
					backupTaskResult.EncryptedKey = r.EncryptedKey
					backupTaskResult.TaskId = taskId
					backupTaskResult.FileName = entry.Name()
					backupTaskResult.FileType = GetFileType(backupTaskResult.FileName)
					backupTaskResult.FileSize = fileInfo.Size()
					backupResultArray = append(backupResultArray, backupTaskResult)
				}

			}

			resultFileName := fmt.Sprintf("dbareport_result_%d.log", r.cfg.Public.MysqlPort)
			if !cmutil.IsDirectory(r.cfg.Public.ResultReportPath) {
				if err := os.MkdirAll(r.cfg.Public.ResultReportPath, 0755); err != nil {
					logger.Log.Errorf("fail to mkdir: %s", r.cfg.Public.ResultReportPath)
				}
			}
			resultFileName = filepath.Join(r.cfg.Public.ResultReportPath, resultFileName)
			resultFile, err := os.OpenFile(resultFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
			if err != nil {
				return err
			}
			defer func() {
				_ = resultFile.Close()
			}()

			for _, value := range backupResultArray {
				backupResultJson, err := json.Marshal(value)
				if err != nil {
					logger.Log.Error("Failed to marshal json encoding data from result data, err: ", err)
					return err
				}
				_, err = resultFile.Write(backupResultJson)
				if err != nil {
					logger.Log.Error("Failed to write json encoding data into result file, err: ", err)
					return err
				}
				_, err = resultFile.WriteString("\n")
				if err != nil {
					logger.Log.Error("Failed to write new line, err: ", err)
					return err
				}
			}
	*/
	return nil
}
