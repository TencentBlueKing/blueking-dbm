package redisbinlogbackup

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"gorm.io/gorm"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/models/mysqlite"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
)

// globRedisBinlogBakJob global var
var globRedisBinlogBakJob *Job
var binlogOnce sync.Once

// Job 例行备份任务
type Job struct { // NOCC:golint/naming(其他:设计如此)
	Conf          *config.Configuration `json:"conf"`
	Tasks         []*Task               `json:"tasks"`
	RealBackupDir string                `json:"real_backup_dir"` // 如 /data/dbbak
	Reporter      report.Reporter       `json:"-"`
	backupClient  backupsys.BackupClient
	sqdb          *gorm.DB
	Err           error `json:"-"`
}

// GetGlobRedisBinlogBackupJob 新建例行binlog备份任务
func GetGlobRedisBinlogBackupJob(conf *config.Configuration) *Job {
	binlogOnce.Do(func() {
		globRedisBinlogBakJob = &Job{
			Conf: conf,
		}
	})
	return globRedisBinlogBakJob
}

// Run 执行例行备份
func (job *Job) Run() {
	mylog.Logger.Info("redisbinlogbackup wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("redisbinlogbackup end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("redisbinlogbackup end succ")
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

	// job.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisBinlogTAG)
	job.backupClient, job.Err = backupsys.NewCosBackupClient(consts.COSBackupClient,
		consts.COSInfoFile, consts.RedisBinlogTAG, job.Conf.BackupClientStrorageType)
	if job.Err != nil {
		if strings.HasPrefix(job.Err.Error(), "backup_client path not found") {
			mylog.Logger.Debug(fmt.Sprintf("backup_client path:%s not found", consts.COSBackupClient))
			job.Err = nil
		} else {
			return
		}
	}
	job.createTasks()
	if job.Err != nil {
		return
	}
	// 本地串行备份
	for _, task := range job.Tasks {
		bakTask := task
		bakTask.BackupLocalBinlogs()
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
			job.DeleteTooOldBinlogbackup(port)
			job.CheckOldBinlogBackupStatus(port)
		}
	}
}

// GetRealBackupDir 获取本地binlog保存路径
func (job *Job) GetRealBackupDir() {
	job.RealBackupDir = consts.GetRedisBackupDir()
	job.RealBackupDir = filepath.Join(job.RealBackupDir, "dbbak")
	util.LocalDirChownMysql(job.RealBackupDir)
}

// GetReporter 上报者
func (job *Job) GetReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "redis")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	reportFile := fmt.Sprintf(consts.RedisBinlogRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	job.Reporter, job.Err = report.NewFileReport(filepath.Join(reportDir, reportFile))
}

func (job *Job) getSqlDB() {
	job.sqdb, job.Err = mysqlite.GetLocalSqDB()
	if job.Err != nil {
		return
	}
	job.Err = job.sqdb.AutoMigrate(&RedisBinlogHistorySchema{})
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
	var task *Task
	var password string
	var taskBackupDir string
	var instStr string

	job.Tasks = []*Task{}
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
			taskBackupDir = filepath.Join(job.RealBackupDir, "binlog", strconv.Itoa(port))
			util.MkDirsIfNotExists([]string{taskBackupDir})
			util.LocalDirChownMysql(taskBackupDir)
			task, job.Err = NewBinlogBackupTask(svrItem.BkBizID, svrItem.BkCloudID,
				svrItem.ClusterDomain, svrItem.ServerIP, port, password,
				job.Conf.RedisBinlogBackup.ToBackupSystem,
				taskBackupDir, svrItem.ServerShards[instStr],
				job.Conf.RedisBinlogBackup.OldFileLeftDay,
				job.Reporter,
				job.Conf.BackupClientStrorageType,
				job.sqdb)
			if job.Err != nil {
				return
			}
			job.Tasks = append(job.Tasks, task)
		}
	}
}

// CheckOldBinlogBackupStatus 重试备份系统上传失败的,检查备份系统上传中的是否成功
func (job *Job) CheckOldBinlogBackupStatus(port int) {
	mylog.Logger.Debug(fmt.Sprintf("port:%d start CheckOldBinlogBackupStatus", port))
	toCheckRows := []RedisBinlogHistorySchema{}
	var taskStatus int
	var statusMsg string
	job.Err = job.sqdb.Where("status not in (?,?,?)",
		consts.BackupStatusToBakSysSuccess,
		consts.BackupStatusFailed,
		consts.BackupStatusLocalSuccess,
	).Find(&toCheckRows).Error
	if job.Err != nil && job.Err != gorm.ErrRecordNotFound {
		job.Err = fmt.Errorf("CheckOldBinlogBackupStatus gorm find fail,err:%v", job.Err)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	job.Err = nil
	mylog.Logger.Debug(fmt.Sprintf("port:%d CheckOldBinlogBackupStatus toCheckRowsCnt:%d", port, len(toCheckRows)))
	for _, row := range toCheckRows {
		if row.Status == consts.BackupStatusToBakSystemFailed && job.backupClient != nil {
			// 重试备份系统上传失败的
			if !util.FileExists(row.BackupFile) {
				continue
			}
			mylog.Logger.Info(fmt.Sprintf("redis(%s) binlog:%+v retry upload backupSystem", row.Addr(), row.BackupFile))
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

// DeleteTooOldBinlogbackup 删除 OldFileLeftDay天前的本地文件,15天前的记录
func (job *Job) DeleteTooOldBinlogbackup(port int) {
	var toDoRows []RedisBinlogHistorySchema
	var err error
	var removeOK bool
	NDaysAgo := time.Now().Local().AddDate(0, 0, -job.Conf.RedisFullBackup.OldFileLeftDay)
	Days15Ago := time.Now().Local().AddDate(0, 0, -15)
	mylog.Logger.Debug(fmt.Sprintf("port:%d start DeleteTooOldBinlogbackup", port))

	// 15 天以前的,本地文件已删除的,记录直接删除
	job.Err = job.sqdb.Where("start_time<=? and local_file_removed=?", Days15Ago, 1).
		Delete(&RedisBinlogHistorySchema{}).Error
	if job.Err != nil {
		job.Err = fmt.Errorf(
			"DeleteTooOldBinlogbackup gorm delete fail,err:%v,start_time:(%s) local_file_removed:%d",
			job.Err, Days15Ago, 1)
		mylog.Logger.Error(job.Err.Error())
		return
	}
	// OldFileLeftDay天以以前的,本地文件未删除的,remove本地文件,并记录下该行为
	job.Err = job.sqdb.Where("start_time<=? and local_file_removed=?", NDaysAgo, 0).Find(&toDoRows).Error
	if job.Err != nil && job.Err != gorm.ErrRecordNotFound {
		job.Err = fmt.Errorf("DeleteTooOldBinlogbackup gorm find fail,err:%v", job.Err)
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
