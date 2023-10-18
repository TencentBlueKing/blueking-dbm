// Package redisfullbackup redis备份任务
package redisfullbackup

import (
	"fmt"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"

	"go.uber.org/zap"
)

// GlobRedisFullCheckJob global var
var GlobRedisFullCheckJob *CheckJob

// CheckJob TODO
// Job 例行备份任务
type CheckJob struct { // NOCC:golint/naming(其他:设计如此)
	Job
}

// InitGlobRedisFullCheckJob 新建例行备份任务
func InitGlobRedisFullCheckJob(conf *config.Configuration) {
	GlobRedisFullCheckJob = &CheckJob{
		Job: Job{
			Conf: conf,
		},
	}
}

// Run 执行例行备份
func (job *CheckJob) Run() {
	mylog.Logger.Info("redisfullbackup wakeup,start running...", zap.String("conf", util.ToString(job.Conf)))
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

	// job.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisFullBackupTAG)
	job.backupClient, job.Err = backupsys.NewCosBackupClient(consts.COSBackupClient, "", consts.RedisFullBackupTAG)
	if job.Err != nil {
		return
	}

	// 检查历史备份任务状态 并 删除过旧的本地文件
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			job.CheckOldFullbackupStatus(port)
			job.DeleteTooOldFullbackup(port)
		}
	}
}
