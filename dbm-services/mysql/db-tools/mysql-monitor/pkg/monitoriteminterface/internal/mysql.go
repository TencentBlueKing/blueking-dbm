package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"

	"github.com/jmoiron/sqlx"
)

func ConnectMySQL() (*sqlx.DB, error) {
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
		return nil, err
	}
	return db, nil //&ConnectionCollect{MySqlDB: db}, nil
}
