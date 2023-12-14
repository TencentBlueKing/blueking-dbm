// Package redisfullbackup redis备份任务
package redisfullbackup

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/models/mysqlite"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"

	"gorm.io/gorm"
)

// globRedisFullBackupJob global var
var globRedisFullBackupJob *Job
var fullOnce sync.Once

// Job 例行备份任务
type Job struct { // NOCC:golint/naming(其他:设计如此)
	Conf          *config.Configuration `json:"conf"`
	Tasks         []*BackupTask         `json:"tasks"`
	RealBackupDir string                `json:"real_backup_dir"`
	Reporter      report.Reporter       `json:"-"`
	backupClient  backupsys.BackupClient
	sqdb          *gorm.DB
	Err           error `json:"-"`
}

// GetGlobRedisFullBackupJob 新建例行备份任务
func GetGlobRedisFullBackupJob(conf *config.Configuration) *Job {
	fullOnce.Do(func() {
		globRedisFullBackupJob = &Job{
			Conf: conf,
		}
	})
	return globRedisFullBackupJob
}

// Run 执行例行备份
func (job *Job) Run() {
	mylog.Logger.Info("redisfullbackup wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("redisfullbackup end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("redisfullbackup end succ")
		}
	}()
	job.Err = nil
	job.GetRealBackupDir()
	if job.Err != nil {
		return
	}
	job.GetReporter()
	if job.Err != nil {
		return
	}
	defer job.Reporter.Close()

	job.getSqlDB()
	if job.Err != nil {
		return
	}
	defer job.closeDB()

	// job.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisFullBackupTAG)
	job.backupClient, job.Err = backupsys.NewCosBackupClient(consts.COSBackupClient,
		consts.COSInfoFile, consts.RedisFullBackupTAG, job.Conf.BackupClientStrorageType)
	if job.Err != nil && !strings.HasPrefix(job.Err.Error(), "backup_client path not found") {
		return
	}
	job.Err = nil
	job.createTasks()
	if job.Err != nil {
		return
	}
	// 本地串行备份
	for _, task := range job.Tasks {
		bakTask := task
		bakTask.BakcupToLocal()
		if bakTask.Err != nil {
			job.Err = bakTask.Err
			continue
		}
	}

	// 检查历史备份任务状态 并 删除过旧的本地文件
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			job.DeleteTooOldFullBackup(port)
			job.CheckOldFullbackupStatus(port)
		}
	}
}

// GetRealBackupDir 获取本地全备保存路径
func (job *Job) GetRealBackupDir() {
	job.RealBackupDir = consts.GetRedisBackupDir()
	job.RealBackupDir = filepath.Join(job.RealBackupDir, "dbbak")
	// /data/dbbak/backup 目录需要
	util.MkDirsIfNotExists([]string{
		filepath.Join(job.RealBackupDir, "backup"),
	})
	// util.LocalDirChownMysql(job.RealBackupDir)
}

// GetReporter 上报者
func (job *Job) GetReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "redis")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	reportFile := fmt.Sprintf(consts.RedisFullbackupRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	job.Reporter, job.Err = report.NewFileReport(filepath.Join(reportDir, reportFile))
}

func (job *Job) getSqlDB() {
	job.sqdb, job.Err = mysqlite.GetLocalSqDB()
	if job.Err != nil {
		return
	}
	job.Err = job.sqdb.AutoMigrate(&RedisFullbackupHistorySchema{})
	if job.Err != nil {
		job.Err = fmt.Errorf("RedisFullbackupHistorySchema AutoMigrate fail,err:%v", job.Err)
		mylog.Logger.Info(job.Err.Error())
		return
	}
}

func (job *Job) closeDB() {
	mysqlite.CloseDB(job.sqdb)
}

func (job *Job) createTasks() {
	var task *BackupTask
	var password string
	var instStr string

	mylog.Logger.Info(fmt.Sprintf("start create fullback tasks,Servers:%s", util.ToString(job.Conf.Servers)))
	job.Tasks = []*BackupTask{}

	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			password, job.Err = myredis.GetRedisPasswdFromConfFile(port)
			if job.Err != nil {
				return
			}
			instStr = fmt.Sprintf("%s:%d", svrItem.ServerIP, port)
			task, job.Err = NewFullBackupTask(svrItem.BkBizID, svrItem.BkCloudID,
				svrItem.ClusterDomain, svrItem.ServerIP, port, password,
				job.Conf.RedisFullBackup.ToBackupSystem,
				consts.NormalBackupType, svrItem.CacheBackupMode, job.RealBackupDir,
				job.Conf.RedisFullBackup.TarSplit, job.Conf.RedisFullBackup.TarSplitPartSize,
				svrItem.ServerShards[instStr], job.Reporter,
				job.Conf.BackupClientStrorageType,
				job.sqdb)
			if job.Err != nil {
				return
			}
			job.Tasks = append(job.Tasks, task)
		}
	}
	mylog.Logger.Debug(fmt.Sprintf("redisfullbackup createTasks tasks:%s", util.ToString(job.Tasks)))
}

// CheckOldFullbackupStatus 重试备份系统上传失败的,检查备份系统上传中的是否成功
func (job *Job) CheckOldFullbackupStatus(port int) {
	mylog.Logger.Info(fmt.Sprintf("port:%d start CheckOldFullbackupStatus", port))
	toCheckRows := []RedisFullbackupHistorySchema{}
	var taskStatus int
	var statusMsg string
	job.Err = job.sqdb.Where("status not in (?,?,?)",
		consts.BackupStatusToBakSysSuccess,
		consts.BackupStatusFailed,
		consts.BackupStatusLocalSuccess,
	).Find(&toCheckRows).Error
	if job.Err != nil && job.Err != gorm.ErrRecordNotFound {
		job.Err = fmt.Errorf("CheckOldFullbackupStatus gorm find fail,err:%v", job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	job.Err = nil
	for _, row := range toCheckRows {
		if row.Status == consts.BackupStatusToBakSystemFailed && job.backupClient != nil {
			// 重试备份系统上传失败的
			if !util.FileExists(row.BackupFile) {
				continue
			}
			mylog.Logger.Info(fmt.Sprintf("redis(%s) backupFiles:%+v retry upload backupSystem", row.Addr(), row.BackupFile))
			row.BackupTaskID, job.Err = job.backupClient.Upload(row.BackupFile)
			if job.Err != nil {
				row.Message = job.Err.Error()
			} else {
				row.Status = consts.BackupStatusToBakSystemStart
				row.Message = "上传备份系统中"
			}
			// 更新记录 status 和 message
			job.Err = job.sqdb.Save(&row).Error
			if job.Err != nil {
				job.Err = fmt.Errorf("gorm save fail,err:%v", job.Err)
				mylog.Logger.Error(job.Err.Error())
			}
			continue
		}
		// 判断是否上传成功
		if row.BackupTaskID != "" && job.backupClient != nil {
			taskStatus, statusMsg, job.Err = job.backupClient.TaskStatus(row.BackupTaskID)
			if job.Err != nil {
				// 依然是失败的,下次继续重试
				continue
			}
			// taskStatus>4,上传失败;
			// taskStatus==4,上传成功;
			// taskStatus<4,上传中;
			if taskStatus > 4 {
				if row.Status != consts.BackupStatusToBakSystemFailed { // 失败状态不重复上报
					row.Status = consts.BackupStatusToBakSystemFailed
					row.Message = fmt.Sprintf("上传失败,err:%s", statusMsg)
					row.BackupRecordReport(job.Reporter)
				}
			} else if taskStatus < 4 {
				// 上传中,下次继续探测
				continue
			} else if taskStatus == 4 {
				// 上传成功
				row.Status = consts.BackupStatusToBakSysSuccess
				row.Message = "上传备份系统成功"
				row.BackupRecordReport(job.Reporter)
			}
			// 更新记录 status 和 message
			job.Err = job.sqdb.Save(&row).Error
			if job.Err != nil {
				job.Err = fmt.Errorf("gorm save fail,err:%v", job.Err)
				mylog.Logger.Error(job.Err.Error())
			}
		}
	}
}

// DeleteTooOldFullBackup 删除 OldFileLeftDay天前的本地文件,15天前的记录
func (job *Job) DeleteTooOldFullBackup(port int) {
	var toDoRows []RedisFullbackupHistorySchema
	var err error
	var removeOK bool
	NDaysAgo := time.Now().Local().AddDate(0, 0, -job.Conf.RedisFullBackup.OldFileLeftDay)
	Days15Ago := time.Now().Local().AddDate(0, 0, -15)
	mylog.Logger.Info(fmt.Sprintf("port:%d start DeleteTooOldFullBackup", port))

	// 15 天以前的,本地文件已删除的,记录直接删除
	job.Err = job.sqdb.Where("start_time<=? and local_file_removed=?", Days15Ago, 1).
		Delete(&RedisFullbackupHistorySchema{}).Error
	if job.Err != nil {
		job.Err = fmt.Errorf(
			"DeleteTooOldFullBackup gorm delete fail,err:%v,start_time:(%s) local_file_removed:%d",
			job.Err, Days15Ago, 1)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	// OldFileLeftDay天以以前的,本地文件未删除的,remove本地文件,并记录下该行为
	job.Err = job.sqdb.Where("start_time<=? and local_file_removed=?", NDaysAgo, 0).Find(&toDoRows).Error
	if job.Err != nil && job.Err != gorm.ErrRecordNotFound {
		job.Err = fmt.Errorf("DeleteTooOldFullBackup gorm find fail,err:%v", job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	job.Err = nil
	for _, row := range toDoRows {
		removeOK = true
		if util.FileExists(row.BackupFile) {
			err = os.Remove(row.BackupFile)
			if err != nil {
				err = fmt.Errorf("os.Remove fail,err:%v,file:%s", err, row.BackupFile)
				mylog.Logger.Warn(err.Error())
				removeOK = false
			}
		}
		if !removeOK {
			continue // 删除失败的,下次继续重试
		}
		row.LocalFileRemoved = 1
		job.Err = job.sqdb.Save(&row).Error
		if job.Err != nil {
			job.Err = fmt.Errorf("gorm save fail,err:%v", job.Err)
			mylog.Logger.Error(job.Err.Error())
		}
	}
}
