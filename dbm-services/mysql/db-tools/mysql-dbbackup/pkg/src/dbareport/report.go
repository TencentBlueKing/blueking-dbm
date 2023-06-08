// Package dbareport TODO
package dbareport

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
)

// Reporter TODO
type Reporter struct {
	Cnf  *parsecnf.Cnf
	Uuid string
}

// NewReporter TODO
func NewReporter(cnf *parsecnf.Cnf) (reporter *Reporter, err error) {
	reporter = &Reporter{
		Cnf: cnf,
	}
	if cnf.Public.BackupId != "" {
		reporter.Uuid = cnf.Public.BackupId
	} else {
		reporter.Uuid, err = GenerateUUid()
		if err != nil {
			return nil, err
		}
	}

	return reporter, nil
}

// ReportCnf Report Cnf info
func (r *Reporter) ReportCnf() error {
	cnfJson, err := json.Marshal(r.Cnf)
	// cnfJson, err := json.MarshalIndent(cnf, "", "")
	if err != nil {
		logger.Log.Error("Failed to marshal json enconding data from Cnf, err: ", err)
		return err
	}
	cnfFileName := "dbareport_cnf_" + r.Cnf.Public.MysqlPort + ".log"
	/*filedir, err := os.Executable()
	if err != nil {
		return err
	}
	filedir = filepath.Dir(filedir)*/
	filedir := "/home/mysql/dbareport/dbbackup/"
	cnfFileName = filepath.Join(filedir, cnfFileName)
	cnfFile, err := os.OpenFile(cnfFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}
	defer cnfFile.Close()

	_, err = cnfFile.Write(cnfJson)
	if err != nil {
		logger.Log.Error("Failed to write json enconding data into cnf file, err: ", err)
		return err
	}
	_, err = cnfFile.WriteString("\n")
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
	nBackupStatus.BillId = r.Cnf.Public.BillId
	nBackupStatus.ClusterId = r.Cnf.Public.ClusterId
	currentTime := time.Now().Format("2006-01-02 15:04:05")
	nBackupStatus.ReportTime = currentTime

	statusJson, err := json.Marshal(nBackupStatus)
	// statusJson, err := json.MarshalIndent(nBackupStatus, "", "")
	if err != nil {
		logger.Log.Error("Failed to marshal json enconding data from status, err: ", err)
		return err
	}
	statusFileName := "dbareport_status_" + r.Cnf.Public.MysqlPort + ".log"
	/*filedir, err := os.Executable()
	if err != nil {
		return err
	}
	filedir = filepath.Dir(filedir)*/
	// filedir := "/home/mysql/dbareport/dbbackup/"
	if !cmutil.IsDirectory(r.Cnf.Public.StatusReportPath) {
		if err := os.MkdirAll(r.Cnf.Public.StatusReportPath, 0755); err != nil {
			logger.Log.Errorf("fail to mkdir: %s", r.Cnf.Public.StatusReportPath)
		}
	}
	statusFileName = filepath.Join(r.Cnf.Public.StatusReportPath, statusFileName)
	statusFile, err := os.OpenFile(statusFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}
	defer statusFile.Close()

	_, err = statusFile.Write(statusJson)
	if err != nil {
		logger.Log.Error("Failed to write json enconding data into status file, err: ", err)
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
	var checksumStr string
	var filesystemStr string
	if r.Cnf.BackupClient.Enable {
		if r.Cnf.BackupClient.DoChecksum {
			checksumStr = "--with-md5"
		} else {
			checksumStr = "--without-md5"
		}
		if strings.ToLower(r.Cnf.BackupClient.RemoteFileSystem) == "hdfs" {
			filesystemStr = "-n"
		} else if strings.ToLower(r.Cnf.BackupClient.RemoteFileSystem) == "cos" {
			filesystemStr = "-c"
		} else {
			err = errors.New("unknown RemoteFileSystem for backupclient")
			return "-1", err
		}
		backupClientStr := fmt.Sprintf(
			`/usr/local/bin/backup_client %s %s -t %s -f %s|grep "taskid"|awk -F: '{print $2}'`,
			filesystemStr,
			checksumStr,
			r.Cnf.BackupClient.FileTag,
			filepath.Join(r.Cnf.Public.BackupDir, fileName),
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
func (r *Reporter) ReportBackupResult(backupBaseResult BackupResult) error {
	var backupResultArray []BackupResult

	dir, err := ioutil.ReadDir(r.Cnf.Public.BackupDir)
	if err != nil {
		logger.Log.Error("failed to read backupdir, err :", err)
		return err
	}

	for _, fi := range dir {
		if fi.IsDir() {
			continue
		} else {
			match := strings.HasPrefix(fi.Name(), common.TargetName)
			if match {
				// execute backup_client, and send file to backup system
				var taskId string
				if taskId, err = r.ExecuteBackupClient(fi.Name()); err != nil {
					return err
				}
				backupTaskResult := backupBaseResult
				backupTaskResult.TaskId = taskId
				backupTaskResult.FileName = fi.Name()
				backupTaskResult.FileType = GetFileType(backupTaskResult.FileName)
				backupTaskResult.FileSize = fi.Size()
				backupResultArray = append(backupResultArray, backupTaskResult)
			}
		}
	}

	resultFileName := "dbareport_result_" + r.Cnf.Public.MysqlPort + ".log"
	/*filedir, err := os.Executable()
	if err != nil {
		return err
	}
	filedir = filepath.Dir(filedir)*/
	// filedir := "/home/mysql/dbareport/dbbackup/"
	if !cmutil.IsDirectory(r.Cnf.Public.ResultReportPath) {
		if err := os.MkdirAll(r.Cnf.Public.ResultReportPath, 0755); err != nil {
			logger.Log.Errorf("fail to mkdir: %s", r.Cnf.Public.ResultReportPath)
		}
	}
	resultFileName = filepath.Join(r.Cnf.Public.ResultReportPath, resultFileName)
	resultFile, err := os.OpenFile(resultFileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}
	defer resultFile.Close()

	for _, value := range backupResultArray {
		backupResultJson, err := json.Marshal(value)
		// backupResultJson, err := json.MarshalIndent(value, "", "")
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
