package mongojob

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/pkg/fileutil"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strconv"
	"sync"
	"time"

	"github.com/pkg/errors"
	"go.uber.org/zap"
)

// backupJobHandle 全局任务句柄
var backupJobHandle *BackupJob
var onceGetBackupJob sync.Once

// NewBackupThread 获取任务句柄 singleInstance
func NewBackupThread(conf *config.DbMonConfig, logger *zap.Logger, jobName string) *BackupJob {
	onceGetBackupJob.Do(func() {
		backupJobHandle = &BackupJob{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
			},
		}
	})
	return backupJobHandle
}

// BackupJob TODO
/*
	MongoDB 例行备份
	每10分钟尝试执行一次，每小时执行一次备份，可能是全备，也可能是增量备份.
*/
// BackupJob 例行备份任务
type BackupJob struct { // NOCC:golint/naming(其他:设计如此)
	basejob.BaseJob
	BackupDir string // 如 /data/dbbak
	ReportDir string // 如 /data/dbbak/dbareport
}

var cleanReportLastTime = int64(0)

// Run 执行例行备份. 被cron对象调用
func (job *BackupJob) Run() {
	job.LoopTimes++
	// try to reload configure file if needed
	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))
	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}
	defer func() {
		job.Logger.Info("end", zap.Uint64("loopTimes", job.LoopTimes))
	}()
	// 存放备份文件的目录
	if err := job.repareBackupDir(); err != nil {
		job.Logger.Error(fmt.Sprintf("prepare backup dir failed, dir:%q err: %v", job.BackupDir, err))
		os.Exit(1)
	}

	// 存放备份报告的目录
	if err := job.prepareReportDir(); err != nil {
		job.Logger.Error(fmt.Sprintf("prepare report dir failed, err: %v", err))
		os.Exit(1)
	}

	nowTime := time.Now()
	if nowTime.Unix()-cleanReportLastTime > 24*3600 {
		// 清理过期的报告文件. 每天执行一次.
		_ = job.cleanReport(nowTime, 90)
		cleanReportLastTime = nowTime.Unix()
	}

	myconf := job.MyConf

	// 遍历所有实例，执行备份，只在Backup节点上备份
	for _, svrItem := range myconf.Servers {
		if svrItem.MetaRole == consts.MetaRoleShardsvrBackup ||
			svrItem.MetaRole == consts.MetaRoleShardsvrBackupNewName {

			// 如果屏蔽告警，也不发起备份.
			if isAlaramShield(&svrItem,
				"skip backup because Shielded", job.Logger) {
				continue
			}

			backupEnable, err := config.ClusterConfig.GetOne(&svrItem, "backup", "enable")
			job.Logger.Debug(fmt.Sprintf("get backup.enable : %s", backupEnable),
				zap.String("instance", svrItem.Addr()), zap.Error(err))
			if backupEnable == "false" {
				job.Logger.Info(
					fmt.Sprintf("cluster config backup.enable is false, skip backup for %s", svrItem.MetaRole),
					zap.String("instance", svrItem.Addr()))
				continue
			}

			zipEnable, _ := config.ClusterConfig.GetOne(&svrItem, "backup", "zip")
			job.Logger.Debug(fmt.Sprintf("get backup.zip : %s", zipEnable))
			archiveEnable, _ := config.ClusterConfig.GetOne(&svrItem, "backup", "archive")
			job.Logger.Debug(fmt.Sprintf("get backup.archive : %s", archiveEnable))
			job.runOneServer(&svrItem, zipEnable == "true", archiveEnable == "true")
		} else {
			job.Logger.Info(fmt.Sprintf("skip backup for %s", svrItem.MetaRole),
				zap.String("instance", svrItem.Addr()))
		}
	}

}

// runOneServer 执行单个实例的备份
func (job *BackupJob) runOneServer(svrItem *config.ConfServerItem, zipEnable bool, archiveEnable bool) {
	// 1，检查实例是否可用
	// 2，检查实例是否需要备份
	// 3，执行备份
	// 4，上报备份结果
	// 备份操作稍微有点复杂，再封装一层
	// backupTask := NewBackupTask(job.Conf, svrItem, job.RealBackupDir, job.Reporter)
	var logger = job.Logger.With(
		zap.String("instance", svrItem.Addr()))
	option := &BackupTaskOption{
		TaskName:           "",
		BackupDir:          job.getBackupDir(),
		BackupType:         "AUTO",
		Host:               svrItem.IP,
		Port:               strconv.Itoa(svrItem.Port),
		User:               svrItem.UserName,
		Password:           svrItem.Password,
		SendToBs:           true,
		RemoveOldFileFirst: true,
		FullFreq:           3600 * 24,
		IncrFreq:           3600,
		Labels:             getBkSvrLabels(svrItem),
		Zip:                zipEnable,
		Archive:            archiveEnable,
	}
	backupTask := NewBackupTask()
	backupTask.Do(option, logger)
}

func getBkSvrLabels(svrItem *config.ConfServerItem) string {
	json, _ := json.Marshal(svrItem.BkDbmLabel)
	return string(json)
}

// getRealBackupDir 备份文件本地路径
func (job *BackupJob) repareBackupDir() error {
	job.BackupDir = job.getBackupDir()
	return fileutil.MkDirsIfNotExists([]string{job.BackupDir})
}

// getBackupDir 日常备份，存放于 /data/dbbak/mg
func (job *BackupJob) getBackupDir() string {
	return path.Join(consts.GetMongoBackupDir(), "dbbak", "mg")
}

// getReporter 上报
func (job *BackupJob) prepareReportDir() error {
	var reportFilePath string
	reportFilePath, job.ReportDir, _ = consts.GetMongoBackupReportPath()
	return report.PrepareReportPath(reportFilePath)
}

// cleanReport delete report file if mtime > 90 day
func (job *BackupJob) cleanReport(nowTime time.Time, reportSavedDays int) error {
	job.Logger.Info("cleanReport start")
	reportFilePath := job.ReportDir
	if reportFilePath == "" {
		job.Logger.Warn("report file path is empty")
	}
	if _, err := os.Stat(reportFilePath); os.IsNotExist(err) {
		job.Logger.Warn(fmt.Sprintf("report file path %s not exist", reportFilePath))
		return nil
	}
	// get files of report dir
	files, err := os.ReadDir(reportFilePath)
	if err != nil {
		job.Logger.Warn(fmt.Sprintf("read report dir %s failed", reportFilePath))
		return nil
	}
	// delete report file if mtime > 90 day
	for _, file := range files {
		filePath := path.Join(reportFilePath, file.Name())
		fileInfo, err := os.Stat(filePath)
		if err != nil {
			job.Logger.Warn(fmt.Sprintf("get file %s info failed", filePath))
			continue
		}
		// now - modTime > 90 days
		if nowTime.Sub(fileInfo.ModTime()) > time.Duration(reportSavedDays)*time.Hour*24 {
			if err := os.Remove(filePath); err != nil {
				job.Logger.Warn(fmt.Sprintf("delete report file %s failed", filePath))
			} else {
				job.Logger.Info(fmt.Sprintf("delete report file %s success", filePath))
			}
		}
	}
	job.Logger.Info("cleanReport end")
	return nil
}

// PrepareDir 准备目录
func (job *BackupJob) PrepareDir() (dirs []string, err error) {
	dir := job.getBackupDir()
	err = fileutil.MkDirsIfNotExists([]string{dir})
	if err != nil {
		return nil, errors.Wrap(err, fmt.Sprintf("prepareBackupDir failed. dir %s", dir))
	}
	err = job.prepareReportDir()
	if err != nil {
		return nil, errors.Wrap(err, fmt.Sprintf("prepareReportDir failed. dir %s", job.ReportDir))
	}
	dirs = append(dirs, dir, job.ReportDir)
	return
}
