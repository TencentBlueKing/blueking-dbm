package backupsys

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// BackupClient TODO
type BackupClient interface {
	Upload(fileName string) (string, error)
	TaskStatus(taskId string) (int, string, error)
}

// BKBackupClient 新备份系统
type BKBackupClient struct {
	backupClient *backupclient.BackupClient
}

// NewCosBackupClient new
func NewCosBackupClient(toolPath string, authFile string, fileTag string) (*BKBackupClient, error) {
	if backupClient, err := backupclient.New(toolPath, authFile, fileTag, ""); err != nil {
		mylog.Logger.Error(fmt.Sprintf("NewCosBackupClient failed,err:%v", err))
		return nil, err
	} else {
		return &BKBackupClient{backupClient: backupClient}, nil
	}
}

// Upload 上传文件
func (o *BKBackupClient) Upload(fileName string) (taskId string, err error) {
	taskId, err = o.backupClient.Upload(fileName)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("CosBackupClient upload failed,err:%v", err))
		return
	}
	return
}

// TaskStatus 备份任务状态
func (o *BKBackupClient) TaskStatus(taskId string) (status int, statusMsg string, err error) {
	status, statusMsg, err = o.backupClient.Query2(taskId)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("CosBackupClient Query2 failed,err:%v", err))
		return
	}
	return
}

// IBSBackupClient 旧备份系统
type IBSBackupClient struct {
	ToolPath string `json:"tool_path"`
	FileTag  string `json:"file_tag"`
}

// NewIBSBackupClient new
func NewIBSBackupClient(toolPath, fileTag string) *IBSBackupClient {
	return &IBSBackupClient{ToolPath: toolPath, FileTag: fileTag}
}

// Upload 上传文件
func (o *IBSBackupClient) Upload(fileName string) (taskId string, err error) {
	bkCmd := fmt.Sprintf("%s -n -f %s --with-md5 -t %s 2>/dev/null|grep 'taskid'|awk -F: '{print $2}'",
		o.ToolPath, fileName, o.FileTag)
	mylog.Logger.Info(bkCmd)
	taskId, err = util.RunBashCmd(bkCmd, "", nil, 10*time.Minute)
	if err != nil {
		return "", err
	}
	if taskId == "" {
		err = fmt.Errorf("%s failed,taskId is empty", bkCmd)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	return taskId, nil
}

// TaskStatus 备份任务状态
func (o *IBSBackupClient) TaskStatus(taskId string) (status int, statusMsg string, err error) {
	ret, err := o.GetTaskStatus(taskId)
	if err != nil {
		return
	}
	return ret.Status, ret.StatusInfo, nil
}

// IBSTaskStatus backup_client  -q --taskid=xxxx 命令的结果
type IBSTaskStatus struct {
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
func (status *IBSTaskStatus) String() string {
	statusBytes, _ := json.Marshal(status)
	return string(statusBytes)
}

// GetTaskStatus 获取备份任务状态
func (o *IBSBackupClient) GetTaskStatus(taskId string) (status IBSTaskStatus, err error) {
	var cmdRet string
	bkCmd := fmt.Sprintf("%s -q --taskid=%s", o.ToolPath, taskId)
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
