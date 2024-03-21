// Package dbmonheartbeat 心跳
package dbmonheartbeat

import (
	"fmt"
	"strconv"
	"sync"

	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/sendwarning"
)

const MongoDbmonHeartBeatMetricName = "mongo_dbmon_heart_beat"

// GlobDbmonHeartbeatJob global var
var globDbmonHeartbeatJob *Job
var dbmonHeartOnce sync.Once

// Job 心跳job
type Job struct {
	Conf *config.Configuration `json:"conf"`
	Name string                `json:"name"`
	Err  error                 `json:"-"`
}

// GetGlobDbmonHeartbeatJob 新建上报心跳任务
func GetGlobDbmonHeartbeatJob(conf *config.Configuration) *Job {
	dbmonHeartOnce.Do(func() {
		globDbmonHeartbeatJob = &Job{
			Conf: conf,
			Name: "dbmonHeartbeat",
		}
	})
	return globDbmonHeartbeatJob
}

// Run 执行例行心跳metric上报 会带第一个实例的维度信息
func (job *Job) Run() {
	mylog.Logger.Info("SendDbmonHeartBeat start")
	if len(job.Conf.Servers) == 0 {
		mylog.Logger.Warn("no server in config")
		return
	}
	err := SendHeartBeat(&job.Conf.BkMonitorBeat, &job.Conf.Servers[0])
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("SendHeartBeat return err %s", err.Error()))
	} else {
		mylog.Logger.Info("SendDbmonHeartBeat done")
	}

}

// SendHeartBeat 发送心跳
func SendHeartBeat(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) error {
	msgH, err := sendwarning.NewBkMonitorEventSender(
		conf.BeatPath,
		conf.AgentAddress,
	)
	if err != nil {
		return err
	}
	return msgH.SetBkBizID(strconv.Itoa(serverConf.BkBizID)).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole).
		SendTimeSeriesMsg(conf.MetricConfig.DataID,
			conf.MetricConfig.Token,
			serverConf.IP,
			MongoDbmonHeartBeatMetricName,
			1)

}
