// Package backupsys 备份系统
package backupsys

import (
	"bufio"
	"bytes"
	"context"
	"crypto/md5"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

const BackupClient = "/usr/local/bin/backup_client"
const UnixTimeLayout = "2006-01-02 15:04:05"

// DoCommand 执行一个命令
func DoCommand(timeoutSecond int64, bin string, args ...string) (bytes.Buffer, bytes.Buffer, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSecond)*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, bin, args...)
	var outBuf, errBuf bytes.Buffer
	cmd.Stdout = &outBuf
	cmd.Stderr = &errBuf
	err := cmd.Run()
	return outBuf, errBuf, err
}

// FileExists 检查目录是否已经存在
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

func splitLines(buffer bytes.Buffer) (map[string]string, error) {
	out := make(map[string]string)
	scanner := bufio.NewScanner(&buffer)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line := scanner.Text()
		log.Printf("read line %q\n", line)
		fs := strings.SplitN(line, ":", 2)
		if len(fs) != 2 {
			continue
		}
		key := strings.TrimSpace(fs[0])
		value := strings.TrimSpace(fs[1])
		out[key] = value
	}

	if scanner.Err() != nil {
		return out, scanner.Err()
	}
	return out, nil
}

// UploadFile 上传一个文件 重试3次 每次60秒超时.
// todo 支持新版的备份系统
/*
	输出分析
	sending task......
	send up backup task success!
	taskid:15548340770
*/
func UploadFile(file, tag string) (task *TaskInfo, err error) {
	maxRetryTimes := 3
	for i := 0; i < maxRetryTimes; i++ {
		task, err = _uploadFileOnce(file, tag)
		if err == nil {
			return
		}
		log.Warnf("_uploadFileOnce failed, err: %v. sleep 60 seconds and try again (%d of %d)", err, i+1, maxRetryTimes)
		time.Sleep(time.Second * 60)
	}
	return
}

func _uploadFileOnce(file, tag string) (*TaskInfo, error) {
	absPath, err := filepath.Abs(file)
	if absPath == "" {
		return nil, errors.Wrap(err, "filepath.Abs")
	}
	if FileExists(file) == false {
		return nil, fmt.Errorf("file %s not exists", file)
	}
	if FileExists(BackupClient) == false {
		return nil, fmt.Errorf("BackupClient %s is not exists", BackupClient)
	}
	fileSize, _ := util.GetFileSize(absPath)
	timeoutSecond := fileSize/1024/1024/1024 + 60 // --with-md5 会计算md5，所以超时时间要加长一点
	outBuf, errBuffer, err := DoCommand(timeoutSecond, BackupClient, "-n", "-f", absPath, "--with-md5", "-t", tag)
	if err != nil {
		return nil, err
	}
	out, _ := splitLines(outBuf)
	taskId, ok := out["taskid"]
	if !ok {
		return nil, fmt.Errorf("failed, stdout:%s, stderr:%s", outBuf.String(), errBuffer.String())
	}
	return &TaskInfo{TaskId: taskId, FilePath: absPath, Tag: tag}, nil
}

// md5String get md5 of string
func md5String(s string) string {
	return fmt.Sprintf("%x", md5.Sum([]byte(s)))
}

// LoadInfoFile 获得一个文件的备份系统信息
func LoadInfoFile(fileFullPath string) (*TaskInfo, error) {
	if fileFullPath == "" {
		return nil, fmt.Errorf("empty file path")
	}
	taskInfoFile := getInfoFilePath(fileFullPath)
	if FileExists(taskInfoFile) == false {
		return nil, fmt.Errorf("file %s not exists", taskInfoFile)
	}
	f, err := os.Open(taskInfoFile)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var info TaskInfo
	if err := json.NewDecoder(f).Decode(&info); err != nil {
		return nil, err
	}
	return &info, nil
}

func getInfoFilePath(fileFullPath string) string {
	if fileFullPath == "" {
		return ""
	}
	dir := filepath.Dir(fileFullPath)
	return filepath.Join(dir, fmt.Sprintf("taskinfo.%s", md5String(fileFullPath)))
}

// GetInfoFilePath 获得一个文件的备份系统信息文件路径
func (t *TaskInfo) GetInfoFilePath() string {
	return getInfoFilePath(t.FilePath)
}

// SaveToFile Save TaskInfo.单台机器上的需要备份的文件名是唯一的.
func (t *TaskInfo) SaveToFile() error {
	if t.FilePath == "" {
		return fmt.Errorf("empty file path")
	}
	taskInfoFile := t.GetInfoFilePath()
	content, err := json.Marshal(t)
	if err != nil {
		return err
	}
	return os.WriteFile(taskInfoFile, content, 0644)
}

const TaskStatusDone = "4"

// TaskInfo backup_client  -q --taskid=xxxx 命令的结果
type TaskInfo struct {
	TaskId       string    `json:"taskid"`
	FilePath     string    `json:"file"`
	Tag          string    `json:"tag"`
	Host         string    `json:"host"`
	SendTime     time.Time `json:"sendup_datetime"`
	Status       string    `json:"status"`
	StatusInfo   string    `json:"status_info"`
	StartTime    time.Time `json:"start_time"`
	CompleteTime time.Time `json:"complete_time"`
	ExpireTime   time.Time `json:"expire_time"`
}

func parseBackupClientTime(value string) (time.Time, error) {
	if value == "0000-00-00 00:00:00" {
		return time.Time{}, nil
	}
	return time.ParseInLocation(UnixTimeLayout, value, time.Local)
}

func parseBackupClientTime2(value string, defaultValue time.Time) (time.Time, error) {
	if value == "0000-00-00 00:00:00" {
		return defaultValue, nil
	}
	return time.ParseInLocation(UnixTimeLayout, value, time.Local)
}

// GetTaskInfo 执行backup_client  -q --taskid=xxxx 命令的结果并解析
/*
file            : /data/mysqllog/20006/binlog/binlog20006.031047
host            : 1.1.1.1
sendup datetime : 2023-04-03 09:15:52
status          : 1
status info     : todo
start_time      : 0000-00-00 00:00:00
complete_time   : 0000-00-00 00:00:00
expire_time     : 0000-00-00 00:00:00
*/
func GetTaskInfo(taskid string) (*TaskInfo, error) {
	args := []string{"-q", fmt.Sprintf("--taskid=%s", taskid)}
	outBuf, _, err := DoCommand(10, BackupClient, args...)
	if err != nil {
		return nil, err
	}
	status := &TaskInfo{TaskId: taskid}
	outMap, err := splitLines(outBuf)
	if err != nil {
		return nil, err
	}
	if outMap == nil || len(outMap) == 0 {
		return nil, fmt.Errorf("empty output")
	}

	// 过期时间,设置为一个月后，避免因为解析失败而被提前删除.
	status.ExpireTime = time.Now().Add(time.Hour * 24 * 31)

	for key, value := range outMap {
		switch key {
		case "file":
			status.FilePath = value
		case "host":
			status.Host = value
		case "status":
			status.Status = value
		case "status info":
			status.StatusInfo = value
		case "sendup datetime":
			status.SendTime, err = parseBackupClientTime(value)
		case "start_time":
			status.StartTime, err = parseBackupClientTime(value)
		case "complete_time":
			status.CompleteTime, err = parseBackupClientTime(value)
		case "expire_time":
			status.ExpireTime, err = parseBackupClientTime2(value, time.Now().Add(time.Hour*24*31))
		}
	}
	return status, nil
}
