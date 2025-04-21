package internal

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
	"time"

	"github.com/jmoiron/sqlx"
)

func connectDB(ip string, port int, ca *config.ConnectAuth, withPing bool, isProxyAdmin bool) (db *sqlx.DB, err error) {
	if withPing {
		db, err = sqlx.Connect(
			"mysql", fmt.Sprintf(
				"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s&multiStatements=true",
				ca.User, ca.Password, ip, port,
				"",
				time.Local.String(),
				config.MonitorConfig.InteractTimeout,
			),
		)
		if err != nil {
			slog.Error("connect db with ping", slog.String("err", err.Error()))
			return nil, err
		}
	} else {
		db, err = sqlx.Open(
			"mysql", fmt.Sprintf(
				"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s",
				ca.User, ca.Password, ip, port,
				"",
				time.Local.String(),
				config.MonitorConfig.InteractTimeout,
			),
		)
		if err != nil {
			slog.Error("connect db without ping", slog.String("err", err.Error()))
			return nil, err
		}
		// 没有 ping 可能返回的是一个无效连接
		// proxy admin 端口 用 select version
		// proxy 数据端口用 select 1
		var sr *sqlx.Rows
		if isProxyAdmin {
			sr, err = db.Queryx(`SELECT VERSION`)
		} else {
			sr, err = db.Queryx(`SELECT 1`)
		}
		if err != nil {
			slog.Error("ping proxy failed", slog.String("err", err.Error()))
			return nil, err
		}
		defer func() {
			_ = sr.Close()
		}()
		slog.Info("ping proxy success")
	}

	db.SetConnMaxIdleTime(0)
	db.SetMaxIdleConns(0)
	db.SetConnMaxLifetime(0)

	return db, nil
}
