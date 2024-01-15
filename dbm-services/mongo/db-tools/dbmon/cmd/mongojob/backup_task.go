package mongojob

import (
	"dbm-services/mongo/db-tools/dbmon/mylog"
	"dbm-services/mongo/db-tools/dbmon/pkg/consts"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"fmt"
	"strconv"
)

// BackupTaskOption TODO
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

// BackupTask TODO
type BackupTask struct {
}

// NewBackupTask 创建任务
func NewBackupTask() *BackupTask {
	return &BackupTask{}
}

// Do 执行任务
func (task *BackupTask) Do(option *BackupTaskOption) error {
	// cb := util.NewCmdBuilder()
	cb := mycmd.NewCmdBuilder()
	backupType := "AUTO"
	reportFile, _, _ := consts.GetMongoBackupReportPath()

	cb.Append(consts.GetDbTool(consts.MongoToolKit)).Append("backup", "--type", backupType).
		Append("--host", option.Host).Append("--port", option.Port).
		Append("--user", option.User).Append("--dir", option.BackupDir).
		Append("--pass").AppendPassword(option.Password).
		Append("--fullFreq", strconv.Itoa(option.FullFreq), "--incrFreq", strconv.Itoa(option.IncrFreq)).
		Append("--report-file", reportFile, "--labels", option.Labels)

	if option.SendToBs {
		cb.Append("--send-to-bs")
	}
	if option.RemoveOldFileFirst {
		cb.Append("--remove-old-file-first")
	}

	cmdLine := cb.GetCmdLine("", false)
	mylog.Logger.Info(fmt.Sprintf("cmdLine: %s", cmdLine))

	// cmd, args := cb.GetCmd()
	o, err := cb.Run2(3600 * 24)
	mylog.Logger.Info(
		fmt.Sprintf("Exec %s cost %0.1f Seconds, stdout: %s, stderr %s",
			cmdLine,
			o.End.Sub(o.Start).Seconds(),
			o.OutBuf.String(),
			o.ErrBuf.String()))

	return err
}
