package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"log/slog"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

func ConnectSpider() (sdb *sqlx.DB, ctlDB *sqlx.DB, err error) {
	sdb, err = connectDB(
		config.MonitorConfig.Ip,
		config.MonitorConfig.Port,
		config.MonitorConfig.Auth.Mysql,
		true,
		false,
	)
	if err != nil {
		slog.Error(
			"connect spider",
			slog.String("error", err.Error()),
			slog.String("ip", config.MonitorConfig.Ip),
			slog.Int("port", config.MonitorConfig.Port),
		)
		return nil, nil, err
	}

	// spider_slave 不建立到中控的连接
	// 所以要小心
	if *config.MonitorConfig.Role == "spider_master" {
		ctlPort := config.MonitorConfig.Port + 1000
		ctlDB, err = connectDB(
			config.MonitorConfig.Ip,
			ctlPort,
			config.MonitorConfig.Auth.Mysql,
			true,
			false,
		)
		if err != nil {
			slog.Error(
				"connect ctl",
				slog.String("error", err.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", ctlPort),
			)
			return nil, nil, errors.Wrap(err, "connect spider ctl")
		}
	}

	return sdb, ctlDB, nil //&ConnectionCollect{MySqlDB: db1, CtlDB: db2}, nil
}
