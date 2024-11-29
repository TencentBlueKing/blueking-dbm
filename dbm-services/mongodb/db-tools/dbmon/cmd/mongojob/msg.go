package mongojob

import (
	"fmt"
	"strconv"

	"github.com/pkg/errors"

	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/sendwarning"
)

// GetBkMonitorBeatSender Retrun a BkMonitorEventSender instance
func GetBkMonitorBeatSender(beatConf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) (
	msgH *sendwarning.BkMonitorEventSender, err error) {
	msgH, err = sendwarning.NewBkMonitorEventSender(
		beatConf.BeatPath,
		beatConf.AgentAddress,
	)
	if err != nil {
		return
	}
	msgH.SetBkBizID(strconv.Itoa(serverConf.BkBizID)).
		SetBkCloudID(serverConf.BkCloudID).
		SetBkTargetIp(serverConf.IP).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole).
		SetInstance(serverConf.Addr())
	return
}

// SendEvent 发送告警消息
func SendEvent(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem,
	eventName, warnLevel, warnMsg string) error {

	msgH, err := GetBkMonitorBeatSender(conf, serverConf)
	if err != nil {
		return errors.Wrap(err, "NewBkMonitorEventSender failed")
	}

	err = msgH.SendEventMsg(
		conf.EventConfig.DataID,
		conf.EventConfig.Token,
		eventName, warnMsg, warnLevel, serverConf.IP)

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
