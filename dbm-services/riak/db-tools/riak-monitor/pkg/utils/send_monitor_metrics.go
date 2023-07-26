package utils

import (
	"strconv"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"

	"golang.org/x/exp/maps"
	"golang.org/x/exp/slog"
)

// SendMonitorMetrics 向蓝鲸监控发送监控指标，用于发送心跳
func SendMonitorMetrics(name string, value int64, customDimension map[string]interface{}) {
	// 借助crond发送监控的信息
	crondManager := ma.NewManager(config.MonitorConfig.ApiUrl)
	// 指标的维度信息
	additionDimension := map[string]interface{}{
		"immute_domain":                 config.MonitorConfig.ImmuteDomain,
		"machine_type":                  config.MonitorConfig.MachineType,
		"bk_cloud_id":                   strconv.Itoa(*config.MonitorConfig.BkCloudID),
		"port":                          strconv.Itoa(config.MonitorConfig.Port),
		"bk_target_service_instance_id": strconv.FormatInt(config.MonitorConfig.BkInstanceId, 10),
	}

	if customDimension != nil {
		maps.Copy(additionDimension, customDimension)
	}

	err := crondManager.SendMetrics(
		name,
		value,
		additionDimension,
	)
	if err != nil {
		slog.Error(
			"send metrics", err,
			slog.String("name", name), slog.Int64("value", value),
		)
	}

	slog.Info(
		"send metrics",
		slog.String("name", name), slog.Int64("msg", value),
	)
}
