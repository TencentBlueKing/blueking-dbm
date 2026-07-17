package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
)

func ConnectMySQL() (*pkg.MySQLMonitorDBH, error) {
	db, err := connectDB(
		config.MonitorConfig.Ip,
		config.MonitorConfig.Port,
		config.MonitorConfig.Auth.Mysql,
		true,
		false,
	)
	if err != nil {
		slog.Error(
			fmt.Sprintf("connect %s", config.MonitorConfig.MachineType),
			slog.String("error", err.Error()),
			slog.String("ip", config.MonitorConfig.Ip),
			slog.Int("port", config.MonitorConfig.Port),
		)
		return db, err
	}
	return db, nil
}
