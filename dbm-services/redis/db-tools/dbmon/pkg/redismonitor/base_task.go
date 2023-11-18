package redismonitor

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/pkg/sendwarning"
)

type baseTask struct {
	ServerConf  config.ConfServerItem             `json:"server_conf"`
	Password    string                            `json:"password"`
	eventSender *sendwarning.BkMonitorEventSender `json:"-"`
	Err         error                             `json:"-"`
}

func newBaseTask(conf *config.Configuration, serverConf config.ConfServerItem, passwd string) (task baseTask,
	err error) {
	task = baseTask{
		ServerConf: serverConf,
		Password:   passwd,
	}
	task.eventSender, err = sendwarning.NewBkMonitorEventSender(
		conf.RedisMonitor.BkMonitorEventDataID,
		conf.RedisMonitor.BkMonitorEventToken,
		conf.BeatPath,
		conf.AgentAddress,
	)
	if err != nil {
		return
	}
	task.eventSender.
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
