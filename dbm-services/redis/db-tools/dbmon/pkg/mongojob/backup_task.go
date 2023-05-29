package mongojob

import (
	"fmt"
	"strconv"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
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
}

// BackupTask TODO
type BackupTask struct {
}

// NewBackupTask 创建任务
func NewBackupTask() *BackupTask {
	return &BackupTask{}
}

/*
    my $cmd = "$RealBin/tools/mongo-toolkit-go_Linux backup  --host $host --port $port  --type $dumptype --user $user --pass '$pass'
--dir $dumpdir --send-to-bs --remove-old-file-first --fullFreq 3600 --incrFreq 3500";

*/

// Do TODO
func (task *BackupTask) Do(option *BackupTaskOption) error {
	cb := util.NewCmdBuilder()
	backupType := "AUTO"
	cb.Append(consts.GetDbTool("mg", consts.MongoToolKit)).Append("backup", "--type", backupType).
		Append("--host", option.Host).Append("--port", option.Port).
		Append("--user", option.User).Append("--dir", option.BackupDir).
		Append("--pass").AppendPassword(option.Password).
		Append("--fullFreq", strconv.Itoa(option.FullFreq), "--incrFreq", strconv.Itoa(option.IncrFreq))

	if option.SendToBs {
		cb.Append("--send-to-bs")
	}
	if option.RemoveOldFileFirst {
		cb.Append("--remove-old-file-first")
	}

	cmdLine := cb.GetCmdLine("", false)
	mylog.Logger.Info(fmt.Sprintf("cmdLine: %s", cmdLine))

	cmd := cb.GetCmd()

	o, err := DoCommandWithTimeout(3600*24, cmd[0], cmd[1:]...)
	mylog.Logger.Info(fmt.Sprintf("Exec %s cost %0.1f Seconds, stdout: %s, stderr %s",
		cmdLine,
		o.End.Sub(o.Start).Seconds(),
		o.Stdout.String(),
		o.Stderr.String()))

	return err
}
