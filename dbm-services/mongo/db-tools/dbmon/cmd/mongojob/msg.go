package mongojob

import (
	"fmt"
	"strconv"

	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/dbmon/mylog"
	"dbm-services/mongo/db-tools/dbmon/pkg/sendwarning"
)

// GetBkMonitorEventSender Retrun a BkMonitorEventSender instance
func GetBkMonitorEventSender(beatConf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) (msgH *sendwarning.BkMonitorEventSender, err error) {
	msgH, err = sendwarning.NewBkMonitorEventSender(
		beatConf.BeatPath,
		beatConf.AgentAddress,
	)
	if err != nil {
		return
	}
	msgH.SetBkBizID(strconv.Itoa(serverConf.BkBizID)).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole)
	return
}

// GetBkMonitorMetricSender Retrun a BkMonitorMetricSender instance
func GetBkMonitorMetricSender(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) (
	msgH *sendwarning.BkMonitorEventSender, err error) {
	msgH, err = sendwarning.NewBkMonitorEventSender(
		conf.BeatPath,
		conf.AgentAddress,
	)
	if err != nil {
		return
	}
	msgH.SetBkBizID(strconv.Itoa(serverConf.BkBizID)).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole)
	return
}

// SendEvent 发送告警消息
func SendEvent(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem,
	eventName, warnLevel, warnMsg string) error {

	msgH, err := sendwarning.NewBkMonitorEventSender(
		conf.BeatPath,
		conf.AgentAddress,
	)

	if msgH != nil && err == nil {
		err = msgH.SetBkBizID(strconv.Itoa(serverConf.BkBizID)).
			SetBkCloudID(serverConf.BkCloudID).
			SetApp(serverConf.App).
			SetAppName(serverConf.AppName).
			SetClusterDomain(serverConf.ClusterDomain).
			SetClusterName(serverConf.ClusterName).
			SetClusterType(serverConf.ClusterType).
			SetInstanceRole(serverConf.MetaRole).SendEventMsg(
			conf.EventConfig.DataID,
			conf.EventConfig.Token,
			eventName, warnMsg, warnLevel, serverConf.IP)
	}

	if err != nil {
		mylog.Logger.Warn(
			fmt.Sprintf("SendEvent failed，name:%s level:%s warnMsg:%q err: %+v",
				eventName, warnLevel, warnMsg, err))
	} else {
		mylog.Logger.Info(
			fmt.Sprintf("SendEvent success，name:%s level:%s warnMsg:%q",
				eventName, warnLevel, warnMsg))
	}

	return err
}
