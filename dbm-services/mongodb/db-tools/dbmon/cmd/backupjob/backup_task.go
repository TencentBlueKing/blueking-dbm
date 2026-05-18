package backupjob

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"fmt"
	"strconv"
	"time"

	"go.uber.org/zap"
)

// BackupTaskOption 备份任务参数
type BackupTaskOption struct {
	// TaskName 任务名称
	TaskName string `json:"task_name"`
	// BackupDir 备份目录
	BackupDir string `json:"backup_dir"`
	// BackupType 备份类型
	BackupType             string `json:"backup_type"`
	Host                   string `json:"host"`
	Port                   string `json:"port"`
	User                   string `json:"user"`
	Password               string `json:"password"`
	SendToBs               bool   `json:"send_to_bs"`
	RemoveOldFileFirst     bool   `json:"remove_old_file_first"`
	MaxDiskUsage           string `json:"max_disk_usage"`
	MinDiskUsage           string `json:"min_disk_usage"`
	FullFreq               int    `json:"full_freq"`
	IncrFreq               int    `json:"incr_freq"`
	Labels                 string `json:"labels"`
	Zip                    bool   `json:"zip"`
	Archive                bool   `json:"archive"`
	NumParallelCollections int    `json:"num_parallel_collections"`
}

// BackupTask 备份任务
type BackupTask struct {
}

// exitCodeBackupLocked 与 mongo-toolkit-go 的 tools.ExitCodeBackupLocked 对齐。
// 子进程拿不到 port 维度的 flock 时返回该退出码，dbmon 据此识别"上一轮还在跑、本轮跳过"，
// 只打 INFO 日志，不当作备份失败上报。
const exitCodeBackupLocked = 75

// backupCmdTimeout 单次备份命令执行超时。
// 历史值为 48h，对大实例（高数据量、归档 + 上传备份系统）会被强制中断。
// 调整为 7d，与 dbmon 自身 dump.log 保留 15d、report 保留 90d 的清理周期对齐，
// 留足以正常完成的窗口；真正卡死的进程仍可通过 flock 互斥被下一轮跳过。
const backupCmdTimeout = time.Hour * 24 * 7

// NewBackupTask 创建任务
func NewBackupTask() *BackupTask {
	return &BackupTask{}
}

// Do 执行任务
// 组装命令行，调用MongoToolKit执行备份任务，返回错误
// 调用MongoToolKit执行备份任务的原因是，MongoToolKit已经实现了备份的逻辑，不需要重复实现
// 也可实现备份时可重启dbmon，但目前没有实现
func (task *BackupTask) Do(option *BackupTaskOption, logger *zap.Logger) error {
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
		if option.MaxDiskUsage != "" {
			cb.Append("--max-disk-usage", option.MaxDiskUsage)
		}
		if option.MinDiskUsage != "" {
			cb.Append("--min-disk-usage", option.MinDiskUsage)
		}
	}

	if option.Zip {
		cb.Append("--zip")
	}

	if option.Archive {
		cb.Append("--archive")
	}

	if option.NumParallelCollections > 0 {
		cb.Append("--numParallelCollections", strconv.Itoa(option.NumParallelCollections))
	}

	// dbmon的日志不上传Es，可以打印密码.
	cmdLine := cb.GetCmdLine2(false)
	logger.Info(fmt.Sprintf("cmdLine: %s", cmdLine))

	o, err := cb.Run(backupCmdTimeout)
	logger.Info(
		fmt.Sprintf("Exec %s cost %0.1f Seconds, stdout: %s, stderr %s",
			cmdLine,
			o.End.Sub(o.Start).Seconds(),
			o.GetStdout(),
			o.GetStderr()))

	if err != nil && o.ExitCode == exitCodeBackupLocked {
		logger.Info(fmt.Sprintf(
			"skip backup: another backup is still running on %s:%s (exit=%d)",
			option.Host, option.Port, o.ExitCode))
		return nil
	}

	return err
}
