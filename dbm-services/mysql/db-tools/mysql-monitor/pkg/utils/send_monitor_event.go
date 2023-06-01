package utils

import (
	"strconv"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"golang.org/x/exp/slog"
)

// SendMonitorEvent TODO
func SendMonitorEvent(name string, msg string) {
	crondManager := ma.NewManager(config.MonitorConfig.ApiUrl)

	additionDimension := map[string]interface{}{
		"immute_domain":                 config.MonitorConfig.ImmuteDomain,
		"machine_type":                  config.MonitorConfig.MachineType,
		"bk_cloud_id":                   *config.MonitorConfig.BkCloudID,
		"port":                          config.MonitorConfig.Port,
		"bk_target_service_instance_id": strconv.FormatInt(config.MonitorConfig.BkInstanceId, 10),
	}

	if config.MonitorConfig.Role != nil {
		additionDimension["role"] = *config.MonitorConfig.Role
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
