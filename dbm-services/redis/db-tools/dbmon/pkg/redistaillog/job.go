package redistaillog

import (
	"context"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
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

// Run run
func (job *Job) Run() {
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
