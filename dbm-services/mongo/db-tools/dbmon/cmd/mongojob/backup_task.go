package mongojob

import (
	"dbm-services/mongo/db-tools/dbmon/mylog"
	"dbm-services/mongo/db-tools/dbmon/pkg/consts"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"fmt"
	"strconv"
	"time"
)

// BackupTaskOption 备份任务参数
type BackupTaskOption struct {
	// TaskName 任务名称
	TaskName string `json:"task_name"`
	// BackupDir 备份目录
	BackupDir string `json:"backup_dir"`
	// BackupType 备份类型
	BackupType         string `json:"backup_type"`
	Host               string `json:"host"`
	Port               string `json:"port"`
	User               string `json:"user"`
	Password           string `json:"password"`
	SendToBs           bool   `json:"send_to_bs"`
	RemoveOldFileFirst bool   `json:"remove_old_file_first"`
	FullFreq           int    `json:"full_freq"`
	IncrFreq           int    `json:"incr_freq"`
	Labels             string `json:"labels"`
}

// BackupTask 备份任务
type BackupTask struct {
}

// NewBackupTask 创建任务
func NewBackupTask() *BackupTask {
	return &BackupTask{}
}

// Do 执行任务
// 组装命令行，调用MongoToolKit执行备份任务，返回错误
// 调用MongoToolKit执行备份任务的原因是，MongoToolKit已经实现了备份的逻辑，不需要重复实现
// 也可实现备份时可重启dbmon，但目前没有实现
func (task *BackupTask) Do(option *BackupTaskOption) error {

	backupType := "AUTO"
	reportFile, _, _ := consts.GetMongoBackupReportPath()

	cb := mycmd.New(consts.GetDbTool(consts.MongoToolKit), "backup", "--type", backupType,
		"--dir", option.BackupDir,
		"--host", option.Host, "--port", option.Port,
		"--user", option.User, "--pass", mycmd.Password(option.Password)).
		Append("--fullFreq", strconv.Itoa(option.FullFreq), "--incrFreq", strconv.Itoa(option.IncrFreq)).
		Append("--report-file", reportFile, "--labels", option.Labels)

	if option.SendToBs {
		cb.Append("--send-to-bs")
	}

	if option.RemoveOldFileFirst {
		cb.Append("--remove-old-file-first")
	}

	// dbmon的日志不上传Es，可以打印密码.
	cmdLine := cb.GetCmdLine2(false)
	mylog.Logger.Info(fmt.Sprintf("cmdLine: %s", cmdLine))

	o, err := cb.Run2(time.Hour * 24)
	mylog.Logger.Info(
		fmt.Sprintf("Exec %s cost %0.1f Seconds, stdout: %s, stderr %s",
			cmdLine,
			o.End.Sub(o.Start).Seconds(),
			o.OutBuf.String(),
			o.ErrBuf.String()))

	return err
}
