package monitor_item_interface

import (
	"context"
	"fmt"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

// ConnectionCollect TODO
type ConnectionCollect struct {
	MySqlDB      *sqlx.DB // spider 也用这个
	ProxyDB      *sqlx.DB
	ProxyAdminDB *sqlx.DB
	CtlDB        *sqlx.DB
}

// Close TODO
func (c *ConnectionCollect) Close() {
	if c.MySqlDB != nil {
		_ = c.MySqlDB.Close()
	}

	if c.ProxyDB != nil {
		_ = c.ProxyDB.Close()
	}

	if c.ProxyAdminDB != nil {
		_ = c.ProxyAdminDB.Close()
	}

	if c.CtlDB != nil {
		_ = c.CtlDB.Close()
	}
}

// NewConnectionCollect TODO
func NewConnectionCollect() (*ConnectionCollect, error) {
	switch config.MonitorConfig.MachineType {
	case "backend", "remote":
		db, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Mysql,
		)
		if err != nil {
			slog.Error(
				fmt.Sprintf("connect %s", config.MonitorConfig.MachineType), err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}
		return &ConnectionCollect{MySqlDB: db}, nil
	case "proxy":
		db1, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Proxy,
		)
		if err != nil {
			slog.Error(
				"connect proxy", err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}

		adminPort := config.MonitorConfig.Port + 1000
		db2, err := connectDB(
			config.MonitorConfig.Ip,
			adminPort,
			config.MonitorConfig.Auth.ProxyAdmin,
		)
		if err != nil {
			if merr, ok := err.(*mysql.MySQLError); ok {
				if merr.Number == 1105 {
					// 连接 proxy 管理端肯定在这里返回
					return &ConnectionCollect{ProxyDB: db1, ProxyAdminDB: db2}, nil
				}
			}
			slog.Error(
				"connect proxy admin", err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", adminPort),
			)
			return nil, err
		}
		// 这里其实永远到不了, 因为 mysql 协议连接 proxy 管理端必然 err!=nil
		return &ConnectionCollect{ProxyDB: db1, ProxyAdminDB: db2}, nil
	case "spider":
		db1, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Mysql,
		)
		if err != nil {
			slog.Error(
				"connect spider", err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}

		ctlPort := config.MonitorConfig.Port + 1000
		db2, err := connectDB(
			config.MonitorConfig.Ip,
			ctlPort,
			config.MonitorConfig.Auth.Mysql,
		)
		if err != nil {
			slog.Error(
				"connect ctl", err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", ctlPort),
			)
			return nil, err
		}

		return &ConnectionCollect{MySqlDB: db1, CtlDB: db2}, nil
	default:
		err := errors.Errorf(
			"not support machine type: %s",
			config.MonitorConfig.MachineType,
		)
		slog.Error("new connect", err)
		return nil, err
	}
}

func connectDB(ip string, port int, ca *config.ConnectAuth) (*sqlx.DB, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	return sqlx.ConnectContext(
		ctx,
		"mysql", fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s",
			ca.User, ca.Password, ip, port,
			"",
			time.Local.String(),
			config.MonitorConfig.InteractTimeout,
		),
	)
}
