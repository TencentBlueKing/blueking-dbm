package mongojob

import (
	"fmt"
	"strconv"

	"go.uber.org/zap"

	"github.com/pkg/errors"

	"dbm-services/mongodb/db-tools/dbmon/config"
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
		SetClusterDomain(serverConf.ClusterDomain).
		SetClusterName(serverConf.ClusterName).
		SetClusterType(serverConf.ClusterType).
		SetInstanceRole(serverConf.MetaRole).
		SetInstance(serverConf.Addr())
	return
}

// isAlaramShield 是否屏蔽告警. 如果配置了屏蔽，则不发送告警
// 如果屏蔽返回异常，则继续发送告警. 记录一个Error日志
func isAlaramShield(serverConf *config.ConfServerItem, msg string, logger *zap.Logger) bool {
	alarmShield, err := config.NewAlarmConfig(config.ClusterConfig).IsAlarmShield(serverConf)
	logger.Debug("isAlaramShield", zap.Bool("alarm.shielded", alarmShield), zap.Error(err))
	if err != nil {
		logger.Error("get alarm shield failed", zap.Error(err))
		return false
	} else if alarmShield {
		logger.Warn("alarm shielded", zap.String("content", msg))
		return true
	} else {
		return false
	}
}

// SendEvent 发送事件消息. 注意如果配置了屏蔽，则不发送告警
func SendEvent(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem,
	eventName, warnLevel, warnMsg string, logger *zap.Logger) error {
	msgH, err := GetBkMonitorBeatSender(conf, serverConf)
	if err != nil {
		return errors.Wrap(err, "NewBkMonitorEventSender failed")
	}

	if isAlaramShield(serverConf,
		fmt.Sprintf("eventName: %s warnLevel: %s warnMsg: %s ", eventName, warnMsg, warnLevel), logger) {
		return nil
	}

	err = msgH.SendEventMsg(
		conf.EventConfig.DataID,
		conf.EventConfig.Token,
		eventName, warnMsg, warnLevel, serverConf.IP, logger)
	return err
}
