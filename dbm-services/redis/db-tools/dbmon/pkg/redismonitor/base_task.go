package redismonitor

import (
	"fmt"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/sendwarning"
)

type baseTask struct {
	ServerConf  config.ConfServerItem             `json:"server_conf"`
	Password    string                            `json:"password"`
	eventSender *sendwarning.BkMonitorEventSender `json:"-"`
	Err         error                             `json:"-"`
}

func newBaseTask(conf *config.Configuration, serverConf config.ConfServerItem) (task baseTask,
	err error) {
	task = baseTask{
		ServerConf: serverConf,
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
	instAddr := serverConf.ServerIP + ":0"
	if len(serverConf.ServerPorts) > 0 {
		instAddr = fmt.Sprintf("%s:%d", serverConf.ServerIP, serverConf.ServerPorts[0])
	}
	task.eventSender.
		SetBkBizID(serverConf.BkBizID).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole).
		SetInstance(instAddr)
	return
}

func (task *baseTask) getPassword(port int) {
	if task.ServerConf.MetaRole == consts.MetaRolePredixy || task.ServerConf.MetaRole == consts.MetaRoleTwemproxy {
		task.Password, task.Err = myredis.GetProxyPasswdFromConfFlie(port, task.ServerConf.MetaRole)
	} else if consts.IsRedisMetaRole(task.ServerConf.MetaRole) {
		task.Password, task.Err = myredis.GetRedisPasswdFromConfFile(port)
	}
	return
}
