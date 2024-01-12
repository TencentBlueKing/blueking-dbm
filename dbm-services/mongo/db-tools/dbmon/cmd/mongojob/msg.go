package mongojob

import (
	"fmt"

	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/dbmon/mylog"
	"dbm-services/mongo/db-tools/dbmon/pkg/sendwarning"
)

// GetBkMonitorEventSender TODO
func GetBkMonitorEventSender(beatConf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) (msgH *sendwarning.BkMonitorEventSender, err error) {
	msgH, err = sendwarning.NewBkMonitorEventSender(
		beatConf.BeatPath,
		beatConf.AgentAddress,
	)
	if err != nil {
		return
	}
	msgH.SetBkBizID(serverConf.BkBizID).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole)
	return
}

// GetBkMonitorMetricSender TODO
func GetBkMonitorMetricSender(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) (
	msgH *sendwarning.BkMonitorEventSender, err error) {
	msgH, err = sendwarning.NewBkMonitorEventSender(
		conf.BeatPath,
		conf.AgentAddress,
	)
	if err != nil {
		return
	}
	msgH.SetBkBizID(serverConf.BkBizID).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole)
	return
}

// SendEvent TODO
func SendEvent(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem,
	eventName, warnLevel, warnMsg string) error {

	msgH, err := sendwarning.NewBkMonitorEventSender(
		conf.BeatPath,
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
			SetInstanceRole(serverConf.MetaRole).SendEventMsg(
			conf.EventConfig.DataID,
			conf.EventConfig.Token,
			eventName, warnMsg, warnLevel, serverConf.ServerIP)
	}

	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("SendEvent failed，name:%s level:%s warnMsg:%q err: %+v", eventName, warnLevel, warnMsg,
			err))
	} else {
		mylog.Logger.Info(fmt.Sprintf("SendEvent success，name:%s level:%s warnMsg:%q", eventName, warnLevel, warnMsg))
	}

	return err
}
