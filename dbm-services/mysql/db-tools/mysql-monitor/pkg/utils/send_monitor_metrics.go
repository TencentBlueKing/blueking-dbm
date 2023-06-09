package utils

import (
	"strconv"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"golang.org/x/exp/maps"
	"golang.org/x/exp/slog"
)

// SendMonitorMetrics TODO
func SendMonitorMetrics(name string, value int64, customDimension map[string]interface{}) {
	crondManager := ma.NewManager(config.MonitorConfig.ApiUrl)

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

	if config.MonitorConfig.Role != nil {
		additionDimension["role"] = *config.MonitorConfig.Role
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
