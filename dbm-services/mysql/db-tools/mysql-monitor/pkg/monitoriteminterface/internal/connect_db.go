package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
	"time"

	"github.com/jmoiron/sqlx"
)

func connectDB(ip string, port int, ca *config.ConnectAuth, withPing bool, isProxyAdmin bool) (
	dbh *pkg.MySQLMonitorDBH, err error,
) {
	dbh = &pkg.MySQLMonitorDBH{
		DB:   nil,
		Host: ip,
		Port: port,
		User: ca.User,
	}

	if withPing {
		dbh.DB, err = sqlx.Connect(
			"mysql", fmt.Sprintf(
				"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s&multiStatements=true",
				ca.User, ca.Password, ip, port,
				"",
				time.Local.String(),
				config.MonitorConfig.InteractTimeout,
			),
		)
		if err != nil {
			if dbh.DB != nil {
				_ = dbh.DB.Close()
				dbh.DB = nil
			}
			slog.Error("connect db with ping", slog.String("err", err.Error()))
			return
		}
	} else {
		dbh.DB, err = sqlx.Open(
			"mysql", fmt.Sprintf(
				"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s",
				ca.User, ca.Password, ip, port,
				"",
				time.Local.String(),
				config.MonitorConfig.InteractTimeout,
			),
		)
		if err != nil {
			if dbh.DB != nil {
				_ = dbh.DB.Close()
				dbh.DB = nil
			}
			slog.Error("connect db without ping", slog.String("err", err.Error()))
			return
		}
		// 没有 ping 可能返回的是一个无效连接
		// proxy admin 端口 用 select version
		// proxy 数据端口用 select 1
		var sr *sqlx.Rows
		if isProxyAdmin {
			sr, err = dbh.DB.Queryx(`SELECT VERSION`)
		} else {
			sr, err = dbh.DB.Queryx(`SELECT 1`)
		}
		if err != nil {
			if dbh.DB != nil {
				_ = dbh.DB.Close()
				dbh.DB = nil
			}
			slog.Error("ping proxy failed", slog.String("err", err.Error()))
			return
		}
		defer func() {
			_ = sr.Close()
		}()
		slog.Info("ping proxy success")
	}

	dbh.DB.SetConnMaxIdleTime(0)
	dbh.DB.SetMaxIdleConns(0)
	dbh.DB.SetConnMaxLifetime(0)

	return
}
