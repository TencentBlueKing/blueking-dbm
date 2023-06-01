package mysql_connlog

import (
	"context"
	"database/sql"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

var nameMySQLConnLogSize = "mysql-connlog-size"
var nameMySQLConnLogRotate = "mysql-connlog-rotate"
var nameMySQLConnLogReport = "mysql-connlog-report"

var sizeLimit int64 = 1024 * 1024 * 1024 * 2
var speedLimit int64 = 1024 * 1024 * 10

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func(*sqlx.DB) (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var initConnLog sql.NullString
	err = c.db.QueryRowxContext(ctx, `SELECT @@init_connect`).Scan(&initConnLog)
	if err != nil {
		slog.Error("select @@init_connect", err)
		return "", err
	}

	if !initConnLog.Valid {
		slog.Info("init_connect disabled")
		return "", nil
	}

	return c.f(c.db)
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLConnLogSize TODO
func NewMySQLConnLogSize(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLConnLogSize,
		f:    mysqlConnLogSize,
	}
}

// NewMySQLConnLogRotate TODO
func NewMySQLConnLogRotate(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLConnLogRotate,
		f:    mysqlConnLogRotate,
	}
}

// NewMySQLConnLogReport TODO
func NewMySQLConnLogReport(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLConnLogReport,
		f:    mysqlConnLogReport,
	}
}

// RegisterMySQLConnLogSize TODO
func RegisterMySQLConnLogSize() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLConnLogSize, NewMySQLConnLogSize
}

// RegisterMySQLConnLogRotate TODO
func RegisterMySQLConnLogRotate() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLConnLogRotate, NewMySQLConnLogRotate
}

// RegisterMySQLConnLogReport TODO
func RegisterMySQLConnLogReport() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLConnLogReport, NewMySQLConnLogReport
}
