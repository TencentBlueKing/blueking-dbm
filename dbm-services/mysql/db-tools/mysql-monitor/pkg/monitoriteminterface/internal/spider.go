package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"errors"
	"log/slog"
)

func ConnectSpider() (sdb *pkg.MySQLMonitorDBH, ctlDB *pkg.MySQLMonitorDBH, err error) {
	var err1, err2 error

	//goland:noinspection GoResourceLeak
	sdb, err1 = connectDB(
		config.MonitorConfig.Ip,
		config.MonitorConfig.Port,
		config.MonitorConfig.Auth.Mysql,
		true,
		false,
	)
	if err1 != nil {
		slog.Error(
			"connect spider",
			slog.String("error", err1.Error()),
			slog.String("ip", config.MonitorConfig.Ip),
			slog.Int("port", config.MonitorConfig.Port),
		)
		//return sdb, nil, err
	}

	// spider_slave 不建立到中控的连接
	// 所以要小心
	if *config.MonitorConfig.Role == "spider_master" {
		ctlPort := config.MonitorConfig.Port + 1000
		ctlDB, err2 = connectDB(
			config.MonitorConfig.Ip,
			ctlPort,
			config.MonitorConfig.Auth.Mysql,
			true,
			false,
		)
		if err2 != nil {
			slog.Error(
				"connect ctl",
				slog.String("error", err2.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", ctlPort),
			)
			//return sdb, ctlDB, errors.Wrap(err, "connect spider ctl")
		}
	}

	return sdb, ctlDB, errors.Join(err1, err2)
}
