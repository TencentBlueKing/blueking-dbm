// Package dbareport TODO
package dbareport

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// Reporter TODO
type Reporter struct {
	cfg *config.BackupConfig
	// Uuid backup_uuid 代表一次备份
	Uuid string
	// EncryptedKey 如果备份加密，上报加密 key。加密短语 key 会通过 rsa 加密成密文 再上报
	EncryptedKey string
}

// NewReporter TODO
func NewReporter(cfg *config.BackupConfig) (reporter *Reporter, err error) {
	reporter = &Reporter{
		cfg: cfg,
	}
	if cfg.Public.BackupId != "" {
		reporter.Uuid = cfg.Public.BackupId
	} else {
		reporter.Uuid, err = GenerateUUid()
		if err != nil {
			return nil, err
		}
	}
	if cfg.Public.EncryptOpt.EncryptEnable {
		if ekey := cfg.Public.EncryptOpt.GetEncryptedKey(); len(ekey) <= 32 {
			logger.Log.Warnf("Not safe because EncryptPublicKey is not set, key=%s", ekey)
			reporter.EncryptedKey = ekey
		} else {
			logger.Log.Infof("Passphrase encrypted=%s passphrase=%s", ekey, cfg.Public.EncryptOpt.GetPassphrase())
			reporter.EncryptedKey = ekey
		}
	}
	return reporter, nil
}

// ReportCnf Report cfg info, 未启用
func (r *Reporter) ReportCnf() error {
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
func (r *Reporter) ReportBackupStatus(status string) error {
	var nBackupStatus BackupStatus
	nBackupStatus.BackupId = r.Uuid
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
func (r *Reporter) ExecuteBackupClient(fileName string) (taskid string, err error) {
	if r.cfg.BackupClient.Enable {
		backupClient, err := backupclient.New(r.cfg.BackupClient.BackupClientBin, "", r.cfg.BackupClient.FileTag)
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

// ExecuteBackupClient2 execute backup_client which sends files to backup system
func (r *Reporter) ExecuteBackupClient2(fileName string) (taskid string, err error) {
	var checksumStr string
	var filesystemStr string
	if r.cfg.BackupClient.Enable {
		if r.cfg.BackupClient.DoChecksum {
			checksumStr = "--with-md5"
		} else {
			checksumStr = "--without-md5"
		}
		if strings.ToLower(r.cfg.BackupClient.RemoteFileSystem) == "hdfs" {
			filesystemStr = "-n"
		} else if strings.ToLower(r.cfg.BackupClient.RemoteFileSystem) == "cos" {
			filesystemStr = "-c"
		} else {
			err = errors.New("unknown RemoteFileSystem for backupclient")
			return "-1", err
		}
		backupClientStr := fmt.Sprintf(
			`/usr/local/bin/backup_client %s %s -t %s -f %s|grep "taskid"|awk -F: '{print $2}'`,
			filesystemStr,
			checksumStr,
			r.cfg.BackupClient.FileTag,
			filepath.Join(r.cfg.Public.BackupDir, fileName),
		)
		// IMPORTANT: mock success
		backupClientStr = `echo $(date +%s)`
		var stdout, stderr bytes.Buffer
		cmd := exec.Command("/bin/bash", "-c", backupClientStr)
		cmd.Stdout = &stdout
		cmd.Stderr = &stderr
		if err := cmd.Run(); err != nil {
			logger.Log.Error("failed to send file to backup system, err: ", err)
			return "-1", err
		}
		if stderr.String() != "" {
			return "-1", fmt.Errorf("failed to execute backup_client, %s", stderr.String())
		}
		taskid = strings.Replace(stdout.String(), "\n", "", -1)
		logger.Log.Info("execute backup_client, result: ", stdout.String())
	} else {
		taskid = "-1"
	}
	return taskid, nil
}

// ReportBackupResult Report BackupResult info
// 会执行 ExecuteBackupClient  upload
func (r *Reporter) ReportBackupResult(backupBaseResult BackupResult) error {
	var backupResultArray []BackupResult

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

		match := strings.HasPrefix(entry.Name(), r.cfg.Public.TargetName())
		if match {
			// execute backup_client, and send file to backup system
			var taskId string
			fileName := filepath.Join(r.cfg.Public.BackupDir, entry.Name())
			if taskId, err = r.ExecuteBackupClient(fileName); err != nil {
				return err
			}
			backupTaskResult := backupBaseResult
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

	return nil
}
