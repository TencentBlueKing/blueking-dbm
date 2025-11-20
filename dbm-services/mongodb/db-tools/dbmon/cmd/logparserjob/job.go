package logparserjob

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/pkg/myroutine"
	"fmt"
	"slices"
	"sync"
	"time"

	"go.uber.org/zap"
)

const maxTime = 600

// logparseJob
var globJob *Job
var once sync.Once

// Job 心跳job
type Job struct {
	basejob.BaseJob
	Workers []*Worker
	Wg      sync.WaitGroup
}

// 协程池
var onceWorkPool sync.Once
var workPool *myroutine.Pool

// getWorkerPool 协程池
func getWorkerPool(logger *zap.Logger) *myroutine.Pool {
	onceWorkPool.Do(func() {
		workPool = myroutine.NewPool(logger)
	})
	return workPool
}

// GetJob 新建logparse任务
func GetJob(conf *config.DbMonConfig, logger *zap.Logger, jobName string,
	osCtx context.Context, rootWg *sync.WaitGroup) *Job {
	once.Do(func() {
		logger.Info("new logparse job")
		globJob = &Job{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
				OsCtx:  osCtx,
				RootWg: rootWg,
			},
		}
	})
	return globJob
}

// Run do log parser 如果是 v4.4以上，用soft link
// 配置更新后，相应的Job会有Stop或Start或Restart操作
func (job *Job) Run() {
	job.RootWgInit()
	if job.WatchOsCtx() {
		job.RootWgDone() // 通知rootWg，任务已经结束. 重复调用不会有影响
		return
	}
	job.Logger.Info("start")
	todoServer := job.getServers()
	if len(todoServer) == 0 {
		job.Logger.Warn("no server need to parse log")
		return
	}
	p := getWorkerPool(job.Logger)
	job.doParse(p, todoServer)
	job.watchConfigUpdate(p)
	job.Logger.Info("done")
}

// WatchConfigUpdate 监控配置更新. 如果有更新，发信号给相应的Job停止，并重新开始。
func (job *Job) watchConfigUpdate(p *myroutine.Pool) {
	ticker := time.NewTicker(time.Second * 5)
	for {
		select {
		case <-job.OsCtx.Done():
			job.Logger.Info("receive os quit signal, exit")
			p.StopAll()
			time.Sleep(time.Millisecond * 100)
			job.RootWgDone()
			return
		case <-ticker.C:
			job.Logger.Info("watch config update")
			todoServer := job.getServers()
			routines := p.GetRoutineNames()

			addrList := make([]string, 0)
			addCount, delCount := 0, 0
			// 如果有新的server，添加到pool中
			for i := range todoServer {
				server := todoServer[i]
				addrList = append(addrList, server.Addr())
				if slices.Index(routines, server.Addr()) == -1 {
					addCount += 1
					job.Logger.Info(fmt.Sprintf("add new worker %s", server.Addr()))
					p.Add(server.Addr(), NewWorker(&todoServer[i], maxTime, job.Logger, job.OsCtx))
				}
			}

			// 如果有server被删除，从pool中删除
			for _, routine := range routines {
				if slices.Index(addrList, routine) == -1 {
					delCount += 1
					job.Logger.Info(fmt.Sprintf("stop worker %s", routine))
					p.Stop(routine)
					p.Remove(routine)
				}
			}

			if addCount > 0 || delCount > 0 {
				job.Logger.Info(fmt.Sprintf("watchConfigUpdate: add %d, del %d", addCount, delCount))
			}

			p.StartAll() // 启动新增的，或者已Stop的. 保证所有的worker都在运行
			p.Status()
		}
	}
}

func (job *Job) getServers() []config.ConfServerItem {
	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return nil
	}
	var todoServer []config.ConfServerItem
	for _, svrItem := range job.MyConf.Servers {
		parselogEnable, err := config.ClusterConfig.GetOne(&svrItem, "parselog", "enable")
		job.Logger.Debug(fmt.Sprintf("get parselog.enable : %s", parselogEnable),
			zap.String("instance", svrItem.Addr()), zap.Error(err))
		if parselogEnable == "false" {
			job.Logger.Info(
				"cluster config parselog.enable is false, skip parselog",
				zap.String("instance", svrItem.Addr()))
			continue
		}
		todoServer = append(todoServer, svrItem)
	}
	return todoServer
}

// doParse 解析日志文件
func (job *Job) doParse(p *myroutine.Pool, todoServer []config.ConfServerItem) {
	for i, server := range todoServer {
		p.Add(server.Addr(), NewWorker(&todoServer[i], maxTime, job.Logger, job.OsCtx))
	}
	p.StartAll()
}
