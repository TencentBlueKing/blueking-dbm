package redistaillog

import (
	"context"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

var globalRedisTailLogJob *Job
var tailOnce sync.Once

// GetGlobRedisTailLogJob TODO
func GetGlobRedisTailLogJob(conf *config.Configuration) *Job {
	tailOnce.Do(func() {
		globalRedisTailLogJob = &Job{
			Conf: conf,
		}
	})
	return globalRedisTailLogJob
}

// Job TODO
type Job struct {
	Conf  *config.Configuration `json:"conf"`
	Tasks map[string]*TailTask  `json:"tasks"` // key:ip:port
	Ctx   *context.Context      `json:"-"`
	Err   error                 `json:"-"`
}

func (job *Job) createTasks() {
	if job.Tasks == nil {
		job.Tasks = make(map[string]*TailTask)
	}
	var addr string
	var task *TailTask
	for _, svrItem := range job.Conf.Servers {
		if svrItem.MetaRole != consts.MetaRoleRedisMaster &&
			svrItem.MetaRole != consts.MetaRoleRedisSlave &&
			svrItem.MetaRole != consts.MetaRolePredixy &&
			svrItem.MetaRole != consts.MetaRoleTwemproxy {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			addr = svrItem.ServerIP + ":" + strconv.Itoa(port)
			if _, ok := job.Tasks[addr]; !ok {
				task, job.Err = NewTailTask(svrItem, job.Conf.ReportSaveDir, port)
				if job.Err != nil {
					continue
				}
				job.Tasks[addr] = task
			}
		}
	}
}

// ClearOldLogFile 当磁盘空间超过 diskUsgMaxRatio% 时，删除keepNDaysFile天前的旧日志文件
func (job *Job) ClearOldLogFile(diskUsgMaxRatio, keepNDaysFile int) {
	var err error
	var logFile, logDir, findCmd string
	var logDirDiskUsg util.HostDiskUsage
	for _, svrItem := range job.Conf.Servers {
		for _, port := range svrItem.ServerPorts {
			if svrItem.MetaRole != consts.MetaRolePredixy && svrItem.MetaRole != consts.MetaRoleTwemproxy {
				continue
			}
			if svrItem.MetaRole == consts.MetaRolePredixy {
				logFile, err = util.GetPredixyLastLogFile(port)
			} else if svrItem.MetaRole == consts.MetaRoleTwemproxy {
				logFile, err = util.GetTwemproxyLastLogFile(port)
			}
			if err != nil {
				continue
			}
			// 找出logFile所在目录,并获取目录磁盘使用率
			logDir = filepath.Dir(logFile)
			if logDir == "" || logDir == "/" || logDir == "/usr/local" || !util.FileExists(logDir) {
				mylog.Logger.Warn(fmt.Sprintf("%s %s:%d logDir:%s is not exist", svrItem.MetaRole, svrItem.ServerIP, port, logDir))
			}
			logDirDiskUsg, err = util.GetLocalDirDiskUsg(logDir)
			if err != nil {
				mylog.Logger.Error(err.Error())
				continue
			}
			if logDirDiskUsg.UsageRatio < diskUsgMaxRatio {
				continue
			}
			mylog.Logger.Info(fmt.Sprintf("%s %s:%d DIR:%s UsageRatio:%d%%",
				svrItem.MetaRole, svrItem.ServerIP, port, logDir, logDirDiskUsg.UsageRatio))
			// 删除目录下3天前的文件
			findCmd = fmt.Sprintf("find %s -mtime +%d -name *.log|xargs rm -rf", logDir, keepNDaysFile)
			mylog.Logger.Info(findCmd)
			util.RunBashCmd(findCmd, "", nil, 1*time.Minute)
		}
	}
	logDir = consts.RedisReportSaveDir
	if !util.FileExists(logDir) {
		mylog.Logger.Warn(fmt.Sprintf("DIR:%s is not exist", logDir))
	}
	logDirDiskUsg, err = util.GetLocalDirDiskUsg(logDir)
	if err != nil {
		mylog.Logger.Error(err.Error())
		return
	}
	if logDirDiskUsg.UsageRatio < diskUsgMaxRatio {
		return
	}
	mylog.Logger.Info(fmt.Sprintf("DIR:%s UsageRatio:%d%%", logDir, logDirDiskUsg.UsageRatio))
	// 删除目录下3天前的文件
	findCmd = fmt.Sprintf("find %s -mtime +%d -name redis_server_log*.log|xargs rm -rf", logDir, keepNDaysFile)
	mylog.Logger.Info(findCmd)
	util.RunBashCmd(findCmd, "", nil, 1*time.Minute)
}

// Run run
func (job *Job) Run() {
	// 如果磁盘使用率超过70%,先清理3天前的文件
	job.ClearOldLogFile(70, 3)
	// 如果磁盘使用率依然超过70%,继续清理1天前的文件
	job.ClearOldLogFile(70, 1)
	job.Err = nil
	// 如果当时时间是 [0:00:00,0:5:00]之间,则重启所有任务
	// 这样每天都会生成一个上报文件,避免单个上报文件过大
	now := time.Now().Local()
	todayStr := now.Format(consts.FilenameDayLayout)
	if now.Hour() == 0 && now.Minute() < 5 && job.Tasks != nil && len(job.Tasks) > 0 {
		// 如果存在 task.ReportFile 文件名不是'今天'日期,则需要重启task
		for _, tmp := range job.Tasks {
			task := tmp
			if !strings.Contains(task.ReportFile, todayStr) {
				task.StopTailLog()
				delete(job.Tasks, task.Addr())
			}
		}
	}
	job.createTasks()
	if job.Err != nil {
		return
	}
	for _, task := range job.Tasks {
		if len(task.TailObjs) > 0 && task.Err == nil {
			// task 正在运行中,无需重复启动
			continue
		}
		task.RunTailLog()
		if task.Err != nil {
			job.Err = task.Err
		}
	}
}
