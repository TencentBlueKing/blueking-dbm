// Package redisheartbeat 心跳写入
package redisheartbeat

import (
	"sync"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

// globRedisHeartbeatJob global var
var globRedisHeartbeatJob *Job
var heartOnce sync.Once

// Job 心跳job
type Job struct {
	Conf  *config.Configuration `json:"conf"`
	Tasks []*HeartbeatTask      `json:"tasks"`
	Err   error                 `json:"-"`
}

// GetGlobRedisHeartbeatJob 新建更新心跳任务
func GetGlobRedisHeartbeatJob(conf *config.Configuration) *Job {
	heartOnce.Do(func() {
		globRedisHeartbeatJob = &Job{
			Conf: conf,
		}
	})
	return globRedisHeartbeatJob
}

func (job *Job) createTasks() {
	var task *HeartbeatTask
	var password string
	job.Tasks = []*HeartbeatTask{}
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			password, job.Err = myredis.GetRedisPasswdFromConfFile(port)
			if job.Err != nil {
				return
			}
			task = NewHeartbeatTask(svrItem.BkBizID, svrItem.BkCloudID,
				svrItem.ServerIP, port, svrItem.ClusterDomain, password)
			job.Tasks = append(job.Tasks, task)
		}
	}
}

// Run 执行例行备份
func (job *Job) Run() {
	job.Err = nil
	job.createTasks()
	if job.Err != nil {
		return
	}
	// 并发更新心跳
	wg := sync.WaitGroup{}
	genChan := make(chan *HeartbeatTask)
	var limit int = 10 // 并发度10
	for worker := 0; worker < limit; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for taskItem := range genChan {
				taskItem.UpdateHeartbeat()
			}
		}()
	}
	go func() {
		// 关闭genChan,以便让所有goroutine退出
		defer close(genChan)
		for _, task := range job.Tasks {
			bakTask := task
			genChan <- bakTask
		}
	}()
	wg.Wait()
	for _, task := range job.Tasks {
		beatTask := task
		if beatTask.Err != nil {
			job.Err = beatTask.Err
			return
		}
	}
}
