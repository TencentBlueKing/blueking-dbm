package mongojob

import (
	actuator_consts "dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
	"fmt"
	"path"
	"path/filepath"
	"strconv"
	"sync"
	"time"
)

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
				Name: "mongobackup",
			}
		}
	}
	return backupJobHandle
}

// BackupJob TODO
/*
	MongoDB 例行备份，1，每10分钟尝试执行一次.
	1，每小时执行一次备份，可能是全备，也可能是增量备份.

*/
// BackupJob 例行备份任务
type BackupJob struct { // NOCC:golint/naming(其他:设计如此)
	Name string                `json:"name"`
	Conf *config.Configuration `json:"conf"`
	// 	Tasks         []*BackupTask         `json:"tasks"`
	RealBackupDir string          `json:"real_backup_dir"` // 如 /data/dbbak
	Reporter      report.Reporter `json:"-"`
	Err           error           `json:"-"`
}

// Run 执行例行备份. 被cron对象调用
func (job *BackupJob) Run() {
	mylog.Logger.Info(fmt.Sprintf("%s Run start", job.Name))
	defer func() {
		mylog.Logger.Info(fmt.Sprintf("%s Run End, Err: %+v", job.Name, job.Err))
	}()
	job.Err = nil
	job.getRealBackupDir()
	if job.Err != nil {
		return
	}
	// 	job.getReporter()
	// if job.Err != nil {
	//	return
	// }
	// defer job.Reporter.Close()

	// 调用mongodb-toolkit-go backup 来完成
	for _, svrItem := range job.Conf.Servers {
		// 只在Backup节点上备份
		if svrItem.MetaRole != consts.MetaRoleShardsvrBackup {
			continue
		}
		job.runOneServer(&svrItem)
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

	dumpDir := path.Join(actuator_consts.GetMongoBackupDir(), "dbbak", "mg")
	option := &BackupTaskOption{
		TaskName:           "",
		BackupDir:          dumpDir,
		BackupType:         "AUTO",
		Host:               svrItem.ServerIP,
		Port:               strconv.Itoa(svrItem.ServerPorts[0]),
		User:               "root",
		Password:           "root",
		SendToBs:           true,
		RemoveOldFileFirst: true,
		FullFreq:           3600 * 24,
		IncrFreq:           3600,
	}
	backupTask := NewBackupTask()
	backupTask.Do(option)

}

// getRealBackupDir 获取本地binlog保存路径
func (job *BackupJob) getRealBackupDir() {
	job.RealBackupDir = path.Join(actuator_consts.GetMongoBackupDir(), "mg")
	util.MkDirsIfNotExists([]string{job.RealBackupDir})
}

// getReporter 上报者
func (job *BackupJob) getReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "mongo")
	reportFile := fmt.Sprintf(consts.RedisBinlogRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	job.Reporter, job.Err = report.NewFileReport(filepath.Join(reportDir, reportFile))
}
