package mongojob

import (
	"fmt"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/sendwarning"
)

// SendEvent TODO
func SendEvent(conf *config.Configuration, serverConf *config.ConfServerItem,
	eventName, warnLevel, warnMsg string) error {

	msgH, err := sendwarning.NewBkMonitorEventSender(
		conf.RedisMonitor.BkMonitorEventDataID,
		conf.RedisMonitor.BkMonitorEventToken,
		conf.GsePath,
		conf.AgentAddress,
	)

	if msgH != nil && err == nil {
		err = msgH.SetBkBizID(serverConf.BkBizID).
			SetBkCloudID(serverConf.BkCloudID).
			SetApp(serverConf.App).
			SetAppName(serverConf.AppName).
			SetClusterDomain(serverConf.ClusterDomain).
			SetClusterName(serverConf.ClusterName).
			SetClusterType(serverConf.ClusterType).
			SetInstanceRole(serverConf.MetaRole).SendWarning(eventName, warnMsg, warnLevel, serverConf.ServerIP)
	}

	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("SendEvent failed，name:%s level:%s warnMsg:%q err: %+v", eventName, warnLevel, warnMsg,
			err))
	} else {
		mylog.Logger.Info(fmt.Sprintf("SendEvent success，name:%s level:%s warnMsg:%q", eventName, warnLevel, warnMsg))
	}

	return err
}
