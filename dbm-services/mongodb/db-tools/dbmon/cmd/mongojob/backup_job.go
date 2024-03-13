package mongojob

import (
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/util"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strconv"
	"sync"

	"github.com/pkg/errors"
)

/*
	todo:
		存在一个正在执行的备份任务，此时dbmon-mg重启，如何能“接管”上一次的备份任务？
		访问 127.0.0.1:xxx/doing 则等待
*/
// backupJobHandle 全局任务句柄
var backupJobHandle *BackupJob
var lock = &sync.Mutex{}

// GetBackupJob 获取任务句柄 singleInstance
func GetBackupJob(conf *config.Configuration) *BackupJob {
	if backupJobHandle == nil {
		lock.Lock()
		defer lock.Unlock()
		if backupJobHandle == nil {
			backupJobHandle = &BackupJob{
				Conf: conf,
				Name: "backup",
			}
		}
	}
	return backupJobHandle
}

// BackupJob TODO
/*
	MongoDB 例行备份
	每10分钟尝试执行一次，每小时执行一次备份，可能是全备，也可能是增量备份.
*/
// BackupJob 例行备份任务
type BackupJob struct { // NOCC:golint/naming(其他:设计如此)
	Name      string
	Conf      *config.Configuration
	BackupDir string // 如 /data/dbbak
	ReportDir string // 如 /data/dbbak/dbareport
	Err       error
}

// Run 执行例行备份. 被cron对象调用
func (job *BackupJob) Run() {
	mylog.Logger.Info(fmt.Sprintf("%s Run start", job.Name))
	defer func() {
		mylog.Logger.Info(fmt.Sprintf("%s Run End, Err: %+v", job.Name, job.Err))
	}()
	job.Err = nil
	// 存放备份文件的目录
	if err := job.repareBackupDir(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("prepare backup dir failed, dir:%q err: %v", job.BackupDir, err))
		os.Exit(1)
	}
	// 存放备份报告的目录
	if err := job.prepareReportDir(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("prepare report dir failed, err: %v", err))
		os.Exit(1)
	}

	// 调用mongodb-toolkit-go backup 来完成
	for _, svrItem := range job.Conf.Servers {
		// 只在Backup节点上备份
		if svrItem.MetaRole == consts.MetaRoleShardsvrBackup ||
			svrItem.MetaRole == consts.MetaRoleShardsvrBackupNewName {
			job.runOneServer(&svrItem)
		} else {
			mylog.Logger.Info(fmt.Sprintf("skip backup for %s %s", svrItem.MetaRole))
		}
	}

	if job.Err != nil {
		return
	}

}

// runOneServer 执行单个实例的备份
func (job *BackupJob) runOneServer(svrItem *config.ConfServerItem) {
	// 1，检查实例是否可用
	// 2，检查实例是否需要备份
	// 3，执行备份
	// 4，上报备份结果
	// 备份操作稍微有点复杂，再封装一层
	// backupTask := NewBackupTask(job.Conf, svrItem, job.RealBackupDir, job.Reporter)
	option := &BackupTaskOption{
		TaskName:           "",
		BackupDir:          job.getBackupDir(),
		BackupType:         "AUTO",
		Host:               svrItem.ServerIP,
		Port:               strconv.Itoa(svrItem.ServerPort),
		User:               svrItem.UserName,
		Password:           svrItem.Password,
		SendToBs:           true,
		RemoveOldFileFirst: true,
		FullFreq:           3600 * 24,
		IncrFreq:           3600,
		Labels:             getBkSvrLabels(svrItem),
	}
	backupTask := NewBackupTask()
	backupTask.Do(option)
}

func getBkSvrLabels(svrItem *config.ConfServerItem) string {
	json, _ := json.Marshal(svrItem.BkDbmLabel)
	return string(json)
}

// getRealBackupDir 备份文件本地路径
func (job *BackupJob) repareBackupDir() error {
	job.BackupDir = job.getBackupDir()
	return util.MkDirsIfNotExists([]string{job.BackupDir})
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

// PrepareDir 准备目录
func (job *BackupJob) PrepareDir() (dirs []string, err error) {
	dir := job.getBackupDir()
	err = util.MkDirsIfNotExists([]string{dir})
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
