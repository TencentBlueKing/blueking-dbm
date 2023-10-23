package utils

import (
	"strconv"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"

	"golang.org/x/exp/slog"
)

// SendMonitorEvent 向蓝鲸监控发送监控事件
func SendMonitorEvent(name string, msg string) {
	// 借助crond发送监控的信息
	crondManager := ma.NewManager(config.MonitorConfig.ApiUrl)

	// 事件的维度信息
	additionDimension := map[string]interface{}{
		"cluster_domain": config.MonitorConfig.ImmuteDomain,
		"machine_type":   config.MonitorConfig.MachineType,
		"bk_cloud_id":    *config.MonitorConfig.BkCloudID,
		"port":           config.MonitorConfig.Port,
		"instance_port":  config.MonitorConfig.Port,
		"instance_host":  config.MonitorConfig.Ip,
		// 实例id
		"bk_target_service_instance_id": strconv.FormatInt(config.MonitorConfig.BkInstanceId, 10),
	}

	err := crondManager.SendEvent(
		name,
		msg,
		additionDimension,
	)
	if err != nil {
		slog.Error(
			"send event", err,
			slog.String("name", name), slog.String("msg", msg),
		)
	}

	slog.Info(
		"send event",
		slog.String("name", name), slog.String("msg", msg),
	)
}
