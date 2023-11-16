// Package dbmonheartbeat 心跳报告
package dbmonheartbeat

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/sendwarning"
	"fmt"
	"sync"
)

// GlobDbmonHeartbeatJob global var
var globDbmonHeartbeatJob *Job
var dbmonHeartOnce sync.Once

// Job 心跳job
type Job struct {
	Conf *config.Configuration `json:"conf"`
	Task *DbmonHeartbeatTask   `json:"task"`
	Err  error                 `json:"-"`
}

// GetGlobDbmonHeartbeatJob 新建上报心跳任务
func GetGlobDbmonHeartbeatJob(conf *config.Configuration) *Job {
	dbmonHeartOnce.Do(func() {
		globDbmonHeartbeatJob = &Job{
			Conf: conf,
		}
	})
	return globDbmonHeartbeatJob
}

// Run 执行例行心跳metric上报
func (job *Job) Run() {

	task, _ := NewDbmonHeartbeatTask(job.Conf, job.Conf.Servers[0])
	if task.Err != nil {
		return
	}
	err := task.SendHeartbeat()
	if err != nil {
		return
	}
}

// SendHeartbeat 更新心跳信息
func (task *DbmonHeartbeatTask) SendHeartbeat() error {
	err := task.MetricSender.SendDbmonHeartBeat(task.ServerConf.ServerIP)
	if err != nil {
		errMsg := fmt.Sprintf("dbmon hear beat error:%s", err.Error())
		mylog.Logger.Error(errMsg)
		return err
	}
	return nil
}

// DbmonHeartbeatTask 心跳task
type DbmonHeartbeatTask struct { // NOCC:golint/naming(其他:)
	ServerConf   config.ConfServerItem             `json:"server_conf"`
	MetricSender *sendwarning.BkMonitorEventSender `json:"-"`
	Err          error                             `json:"-"`
}

// NewDbmonHeartbeatTask 新建心跳task
func NewDbmonHeartbeatTask(conf *config.Configuration, serverConf config.ConfServerItem) (task DbmonHeartbeatTask,
	err error) {
	task = DbmonHeartbeatTask{
		ServerConf: serverConf,
	}

	task.MetricSender, err = sendwarning.NewBkMonitorEventSender(
		conf.RedisMonitor.BkMonitorMetricDataID,
		conf.RedisMonitor.BkMonitorMetircToken,
		conf.GsePath,
		conf.AgentAddress,
	)
	if err != nil {
		return
	}
	task.MetricSender.
		SetBkBizID(serverConf.BkBizID).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole)
	return
}
