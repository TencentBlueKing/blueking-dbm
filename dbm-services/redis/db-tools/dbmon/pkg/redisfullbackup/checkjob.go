// Package redisfullbackup redis备份任务
package redisfullbackup

import (
	"fmt"
	"sync"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"

	"go.uber.org/zap"
)

// globRedisFullCheckJob global var
var globRedisFullCheckJob *CheckJob
var checkOnce sync.Once

// CheckJob TODO
// Job 例行备份任务
type CheckJob struct { // NOCC:golint/naming(其他:设计如此)
	Job
}

// GetGlobRedisFullCheckJob 新建例行备份任务
func GetGlobRedisFullCheckJob(conf *config.Configuration) *CheckJob {
	checkOnce.Do(func() {
		globRedisFullCheckJob = &CheckJob{
			Job: Job{
				Conf: conf,
			},
		}
	})
	return globRedisFullCheckJob
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
	job.backupClient, job.Err = backupsys.NewCosBackupClient(consts.COSBackupClient,
		consts.COSInfoFile, consts.RedisFullBackupTAG)
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
