package redisbinlogbackup

import (
	"bufio"
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// GlobRedisBinlogBakJob global var
var GlobRedisBinlogBakJob *Job

// Job 例行备份任务
type Job struct { // NOCC:golint/naming(其他:设计如此)
	Conf          *config.Configuration `json:"conf"`
	Tasks         []*Task               `json:"tasks"`
	RealBackupDir string                `json:"real_backup_dir"` // 如 /data/dbbak
	Reporter      report.Reporter       `json:"-"`
	Err           error                 `json:"-"`
}

// InitGlobRedisBinlogBackupJob 新建例行binlog备份任务
func InitGlobRedisBinlogBackupJob(conf *config.Configuration) {
	GlobRedisBinlogBakJob = &Job{
		Conf: conf,
	}
}

// Run 执行例行备份
func (job *Job) Run() {
	mylog.Logger.Info("redisbinlogbackup wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("redisbinlogbackup end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("redisbinlogbackup end succ")
		}
	}()
	job.Err = nil
	job.GetRealBackupDir()
	if job.Err != nil {
		return
	}
	job.GetReporter()
	if job.Err != nil {
		return
	}
	defer job.Reporter.Close()

	// 检查历史备份任务状态 并 删除过旧的本地文件
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			job.CheckOldBinlogBackupStatus(port)
			job.DeleteTooOldBinlogbackup(port)
		}
	}
	job.createTasks()
	if job.Err != nil {
		return
	}
	// 本地串行备份
	for _, task := range job.Tasks {
		bakTask := task
		bakTask.BackupLocalBinlogs()
		if bakTask.Err != nil {
			job.Err = bakTask.Err
			continue
		}
	}
}

// GetRealBackupDir 获取本地binlog保存路径
func (job *Job) GetRealBackupDir() {
	job.RealBackupDir = consts.GetRedisBackupDir()
	job.RealBackupDir = filepath.Join(job.RealBackupDir, "dbbak")
	util.LocalDirChownMysql(job.RealBackupDir)
}

// GetReporter 上报者
func (job *Job) GetReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "redis")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	reportFile := fmt.Sprintf(consts.RedisBinlogRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	job.Reporter, job.Err = report.NewFileReport(filepath.Join(reportDir, reportFile))
}

func (job *Job) createTasks() {
	var task *Task
	var password string
	var taskBackupDir string

	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			password, job.Err = myredis.GetRedisPasswdFromConfFile(port)
			if job.Err != nil {
				return
			}
			taskBackupDir = filepath.Join(job.RealBackupDir, "binlog", strconv.Itoa(port))
			util.MkDirsIfNotExists([]string{taskBackupDir})
			util.LocalDirChownMysql(taskBackupDir)
			task = NewBinlogBackupTask(svrItem.BkBizID, svrItem.BkCloudID,
				svrItem.ClusterDomain, svrItem.ServerIP, port, password,
				job.Conf.RedisBinlogBackup.ToBackupSystem,
				taskBackupDir, job.Conf.RedisBinlogBackup.OldFileLeftDay, job.Reporter)
			job.Tasks = append(job.Tasks, task)
		}
	}
}

// CheckOldBinlogBackupStatus 检查历史binlog备份任务状态
// 1. 遍历 redis_binlog_file_list_${port}_doing 文件
// 2. 已超过时间的任务,删除本地文件,从 redis_binlog_file_list_${port}_doing 中剔除
// 3. 上传备份系统 运行中 or 失败的任务 记录到 redis_binlog_file_list_${port}_doing_temp
// 4. 已成功的任务,记录到 redis_binlog_file_list_${port}_done
// 5. rename redis_binlog_file_list_${port}_doing_temp to redis_binlog_file_list_${port}_doing
func (job *Job) CheckOldBinlogBackupStatus(port int) {
	var doingHandler, tempHandler, doneHandler *os.File
	var line string
	var err error
	var failMsgs []string
	var runningTaskIDs, failedTaskIDs []uint64
	task := Task{}
	oldFileLeftSec := job.Conf.RedisBinlogBackup.OldFileLeftDay * 24 * 3600
	nowTime := time.Now().Local()
	// 示例: /data/dbbak/binlog/30000/redis_binlog_file_list_30000_doing
	doingFile := filepath.Join(job.RealBackupDir, "binlog", strconv.Itoa(port),
		fmt.Sprintf(consts.DoingRedisBinlogFileList, port))
	if !util.FileExists(doingFile) {
		return
	}
	// 示例: /data/dbbak/binlog/30000/redis_binlog_file_list_30000_doing_temp
	tempDoingFile := doingFile + "_temp"
	// 示例: /data/dbbak/binlog/30000/redis_binlog_file_list_30000_done
	doneFile := filepath.Join(job.RealBackupDir, "binlog", strconv.Itoa(port),
		fmt.Sprintf(consts.DoneRedisBinlogFileList, port))

	defer func() {
		if job.Err == nil {
			mylog.Logger.Info(fmt.Sprintf("rename %s to %s", tempDoingFile, doingFile))
			os.Rename(tempDoingFile, doingFile) // rename
		}
	}()

	doingHandler, job.Err = os.Open(doingFile)
	if job.Err != nil {
		job.Err = fmt.Errorf("os.Open file:%s fail,err:%v", doingFile, job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	defer doingHandler.Close()

	doneHandler, job.Err = os.OpenFile(doneFile, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0744)
	if job.Err != nil {
		job.Err = fmt.Errorf("os.OpenFile %s failed,err:%v", doneFile, job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	defer doneHandler.Close()

	tempHandler, job.Err = os.OpenFile(tempDoingFile, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0744)
	if job.Err != nil {
		job.Err = fmt.Errorf("os.OpenFile %s failed,err:%v", tempDoingFile, job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	defer tempHandler.Close()

	scanner := bufio.NewScanner(doingHandler)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line = scanner.Text()
		err = json.Unmarshal([]byte(line), &task)
		if err != nil {
			// json.Unmarshal failed,skip ...
			err = fmt.Errorf("json.Unmarshal fail,err:%s,data:%s,skip it", err, line)
			mylog.Logger.Error(err.Error())
			continue
		}
		task.reporter = job.Reporter
		// 删除旧文件
		if nowTime.Sub(task.BackupFileMTime.Time).Seconds() > float64(oldFileLeftSec) {
			mylog.Logger.Info(fmt.Sprintf("%s start removing...", task.BackupFile))
			if util.FileExists(task.BackupFile) {
				err = os.Remove(task.BackupFile)
				if err != nil {
					err = fmt.Errorf("os.Remove fail,err:%s,file:%s", err, task.BackupFile)
					mylog.Logger.Error(err.Error())
					tempHandler.WriteString(line + "\n") // 删除失败的,记录到temp文件,下次继续重试
				}
				fmt.Printf("remove %s\n", task.BackupFile)
			}
			continue
		}
		// 无需上传备份系统,本地已备份成功的情况
		if task.Status == consts.BackupStatusLocalSuccess {
			doneHandler.WriteString(line + "\n")
			continue
		}
		// 上传备份系统失败的情况,重试上传并写入temp文件中
		if task.Status == consts.BackupStatusToBakSystemFailed {
			task.TransferToBackupSystem()
			if task.Err != nil {
				task.Message = task.Err.Error()
			} else {
				task.Status = consts.BackupStatusToBakSystemStart
				task.Message = "上传备份系统中"
			}
			tempHandler.WriteString(task.ToString() + "\n")
			continue
		}

		// 判断是否上传成功
		if task.BackupTaskID > 0 {
			uploadTask := backupsys.UploadTask{
				Files:   []string{task.BackupFile},
				TaskIDs: []uint64{task.BackupTaskID},
			}
			runningTaskIDs, failedTaskIDs, _, _, _, _, failMsgs, job.Err = uploadTask.CheckTasksStatus()
			if job.Err != nil {
				tempHandler.WriteString(line + "\n") // 获取tasks状态失败,下次重试
				continue
			}
			if len(failedTaskIDs) > 0 {
				if task.Status != consts.BackupStatusFailed { // 失败状态不重复上报
					task.Status = consts.BackupStatusFailed
					task.Message = fmt.Sprintf("上传失败,err:%s", strings.Join(failMsgs, ","))
					task.BackupRecordReport()
					line = task.ToString()
				}
				tempHandler.WriteString(line + "\n") // 上传失败,下次继续重试
			} else if len(runningTaskIDs) > 0 {
				tempHandler.WriteString(line + "\n") // 上传中,下次继续探测
			} else {
				// 上传成功
				task.Status = consts.BackupStatusToBakSysSuccess
				task.Message = "上传备份系统成功"
				task.BackupRecordReport()
				doneHandler.WriteString(task.ToString() + "\n")
			}
		}
		// 其他失败的情况,写到done文件中
		if task.Status == consts.BackupStatusFailed {
			doneHandler.WriteString(line + "\n")
			continue
		}
	}
	if job.Err = scanner.Err(); job.Err != nil {
		job.Err = fmt.Errorf("scanner.Scan fail,err:%v,file:%v", job.Err, doingFile)
		mylog.Logger.Error(job.Err.Error())
		return
	}
}

// DeleteTooOldBinlogbackup 根据 redis_binlog_file_list_{port}_done 删除太旧的本地文件
// 将删除失败 or 不到OldFileLeftDay天数的task继续回写到 redis_binlog_file_list_{port}_done 文件中
func (job *Job) DeleteTooOldBinlogbackup(port int) {
	var doneHandler *os.File
	task := Task{}
	var line string
	var err error
	keepTasks := []string{}
	oldFileLeftSec := job.Conf.RedisBinlogBackup.OldFileLeftDay * 24 * 3600
	nowTime := time.Now().Local()

	// 示例: /data/dbbak/binlog/30000/redis_binlog_file_list_30000_done
	doneFile := filepath.Join(job.RealBackupDir, "binlog",
		strconv.Itoa(port), fmt.Sprintf(consts.DoneRedisBinlogFileList, port))
	if !util.FileExists(doneFile) {
		return
	}

	defer func() {
		if len(keepTasks) > 0 {
			// 回写到 doneFile中
			done02, err01 := os.OpenFile(doneFile, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0755)
			if err01 != nil {
				job.Err = fmt.Errorf("os.Openfile fail,err:%v,file:%s", err01, doneFile)
				mylog.Logger.Error(job.Err.Error())
				return
			}
			defer done02.Close()
			for _, line := range keepTasks {
				done02.WriteString(line + "\n")
			}
		}
	}()
	doneHandler, job.Err = os.Open(doneFile)
	if job.Err != nil {
		job.Err = fmt.Errorf("os.OpenFile %s failed,err:%v", doneFile, job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	defer doneHandler.Close()

	scanner := bufio.NewScanner(doneHandler)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line = scanner.Text()
		err = json.Unmarshal([]byte(line), &task)
		if err != nil {
			// json.Unmarshal failed,skip ...
			err = fmt.Errorf("json.Unmarshal fail,err:%v,data:%s,file:%s", job.Err, line, doneFile)
			mylog.Logger.Warn(err.Error())
			continue
		}
		if nowTime.Sub(task.BackupFileMTime.Time).Seconds() > float64(oldFileLeftSec) {
			if util.FileExists(task.BackupFile) {
				err = os.Remove(task.BackupFile)
				if err != nil {
					err = fmt.Errorf("os.Remove fail,err:%v,file:%s", err, task.BackupFile)
					mylog.Logger.Warn(err.Error())
					keepTasks = append(keepTasks, line) // 删除失败的,下次继续重试
				}
			}
		} else {
			keepTasks = append(keepTasks, line)
		}
	}
	if err = scanner.Err(); err != nil {
		job.Err = fmt.Errorf("scanner.Scan fail,err:%v,file:%v", err, doneFile)
		mylog.Logger.Error(job.Err.Error())
		return
	}
}
