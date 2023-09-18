// Package backupsys 备份系统
package backupsys

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

// UploadTask 操作备份系统
type UploadTask struct {
	Files   []string `json:"files"` // 全路径
	TaskIDs []uint64 `json:"taskids"`
	Tag     string   `json:"tag"`
}

// UploadFiles 上传文件
func (task *UploadTask) UploadFiles() (err error) {
	var taskIDStr string
	var taskIDNum uint64
	if len(task.Files) == 0 {
		return
	}
	if task.Tag == "" {
		err = fmt.Errorf("BackupSystem uploadFiles tag(%s) cannot be empty", task.Tag)
		mylog.Logger.Error(err.Error())
		return
	}
	for _, file := range task.Files {
		if !util.FileExists(file) {
			err = fmt.Errorf("BackupSystem uploadFiles %s not exists", file)
			mylog.Logger.Error(err.Error())
			return
		}
	}
	for _, bkfile := range task.Files {
		bkCmd := fmt.Sprintf("%s -n -f %s --with-md5 -t %s|grep 'taskid'|awk -F: '{print $2}'",
			consts.BackupClient, bkfile, task.Tag)
		mylog.Logger.Info(bkCmd)
		taskIDStr, err = util.RunBashCmd(bkCmd, "", nil, 10*time.Minute)
		if err != nil {
			return
		}
		taskIDNum, err = strconv.ParseUint(taskIDStr, 10, 64)
		if err != nil {
			err = fmt.Errorf("%s ParseUint failed,err:%v", taskIDStr, err)
			mylog.Logger.Error(err.Error())
			return
		}
		task.TaskIDs = append(task.TaskIDs, taskIDNum)
	}
	return
}

// CheckTasksStatus 检查tasks状态
func (task *UploadTask) CheckTasksStatus() (runningTaskIDs, failTaskIDs, succTaskIDs []uint64,
	runningFiles, failedFiles, succFiles []string, failMsgs []string, err error) {
	var status TaskStatus
	for idx, taskID := range task.TaskIDs {
		status, err = GetTaskStatus(taskID)
		if err != nil {
			return
		}
		if status.Status > 4 {
			// err = fmt.Errorf("ToBackupSystem %s failed,err:%s,taskid:%d",
			// 	status.File, status.StatusInfo, taskID)
			// mylog.Logger.Error(err.Error())
			failMsgs = append(failMsgs, fmt.Sprintf("taskid:%d,failMsg:%s", taskID, status.StatusInfo))
			failedFiles = append(failedFiles, task.Files[idx])
			failTaskIDs = append(failTaskIDs, task.TaskIDs[idx])
		} else if status.Status == 4 {
			succFiles = append(succFiles, task.Files[idx])
			succTaskIDs = append(succTaskIDs, task.TaskIDs[idx])
		} else if status.Status < 4 {
			runningFiles = append(runningFiles, task.Files[idx])
			runningTaskIDs = append(runningTaskIDs, task.TaskIDs[idx])
		}
	}
	return
}

// WaitForUploadFinish 等待所有files上传成功
func (task *UploadTask) WaitForUploadFinish() (err error) {
	var times int64
	var msg string
	var runningFiles, failFiles, succFiles, failMsgs []string
	for {
		times++
		_, _, _, runningFiles, failFiles, succFiles, failMsgs, err = task.CheckTasksStatus()
		if err != nil {
			return
		}
		// 只要有running的task,则继续等待
		if len(runningFiles) > 0 {
			if times%6 == 0 {
				// 每分钟打印一次日志
				msg = fmt.Sprintf("files[%+v] cnt:%d upload to backupSystem still running", runningFiles, len(runningFiles))
				mylog.Logger.Info(msg)
			}
			time.Sleep(10 * time.Second)
			continue
		}
		if len(failMsgs) > 0 {
			err = fmt.Errorf("failCnt:%d,failFiles:[%+v],err:%s", len(failFiles), failFiles, strings.Join(failFiles, ","))
			mylog.Logger.Error(err.Error())
			return
		}
		if len(succFiles) == len(task.Files) {
			return nil
		}
		break
	}
	return
}

// TaskStatus backup_client  -q --taskid=xxxx 命令的结果
type TaskStatus struct {
	File           string    `json:"file"`
	Host           string    `json:"host"`
	SednupDateTime time.Time `json:"sendup_datetime"`
	Status         int       `json:"status"`
	StatusInfo     string    `json:"status_info"`
	StartTime      time.Time `json:"start_time"`
	CompleteTime   time.Time `json:"complete_time"`
	ExpireTime     time.Time `json:"expire_time"`
}

// String 用于打印
func (status *TaskStatus) String() string {
	statusBytes, _ := json.Marshal(status)
	return string(statusBytes)
}

// GetTaskStatus 执行backup_client  -q --taskid=xxxx 命令的结果并解析
func GetTaskStatus(taskid uint64) (status TaskStatus, err error) {
	var cmdRet string
	bkCmd := fmt.Sprintf("%s -q --taskid=%d", consts.BackupClient, taskid)
	cmdRet, err = util.RunBashCmd(bkCmd, "", nil, 30*time.Second)
	if err != nil {
		return
	}
	scanner := bufio.NewScanner(strings.NewReader(cmdRet))
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		l01 := strings.SplitN(line, ":", 2)
		if len(l01) != 2 {
			err = fmt.Errorf("len()!=2,cmd:%s,result format not correct:%s", bkCmd, cmdRet)
			mylog.Logger.Error(err.Error())
			return
		}
		first := strings.TrimSpace(l01[0])
		second := strings.TrimSpace(l01[1])
		switch first {
		case "file":
			status.File = second
		case "host":
			status.Host = second
		case "sendup datetime":
			if second == "0000-00-00 00:00:00" {
				status.SednupDateTime = time.Time{} // "0000-01-00 00:00:00"
				break
			}
			status.SednupDateTime, err = time.ParseInLocation(consts.UnixtimeLayout, second, time.Local)
			if err != nil {
				err = fmt.Errorf("time.Parse 'sendup datetime' failed,err:%v,value:%s,cmd:%s", err, second, bkCmd)
				mylog.Logger.Error(err.Error())
				return
			}
		case "status":
			status.Status, err = strconv.Atoi(second)
			if err != nil {
				err = fmt.Errorf("strconv.Atoi failed,err:%v,value:%s,cmd:%s", err, second, bkCmd)
				mylog.Logger.Error(err.Error())
				return
			}
		case "status info":
			status.StatusInfo = second
		case "start_time":
			if second == "0000-00-00 00:00:00" {
				status.StartTime = time.Time{} // "0000-01-00 00:00:00"
				break
			}
			status.StartTime, err = time.ParseInLocation(consts.UnixtimeLayout, second, time.Local)
			if err != nil {
				err = fmt.Errorf("time.Parse start_time failed,err:%v,value:%s,cmd:%s", err, second, bkCmd)
				mylog.Logger.Error(err.Error())
				return
			}
		case "complete_time":
			if second == "0000-00-00 00:00:00" {
				status.CompleteTime = time.Time{} // "0000-01-00 00:00:00"
				break
			}
			status.CompleteTime, err = time.ParseInLocation(consts.UnixtimeLayout, second, time.Local)
			if err != nil {
				err = fmt.Errorf("time.Parse complete_time failed,err:%v,value:%s,cmd:%s", err, second, bkCmd)
				mylog.Logger.Error(err.Error())
				return
			}
		case "expire_time":
			if second == "0000-00-00 00:00:00" {
				status.ExpireTime = time.Time{} // "0000-01-00 00:00:00"
				break
			}
			status.ExpireTime, err = time.ParseInLocation(consts.UnixtimeLayout, second, time.Local)
			if err != nil {
				err = fmt.Errorf("time.Parse expire_time failed,err:%v,value:%s,cmd:%s", err, second, bkCmd)
				mylog.Logger.Error(err.Error())
				return
			}
		}
	}
	if err = scanner.Err(); err != nil {
		err = fmt.Errorf("scanner.Scan failed,err:%v,cmd:%s", err, cmdRet)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}
