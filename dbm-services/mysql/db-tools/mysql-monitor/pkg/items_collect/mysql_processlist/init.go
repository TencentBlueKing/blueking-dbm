package mysql_processlist

import (
	"os"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
)

var stored = false
var executable string

var nameMySQLLock = "mysql-lock"
var nameMySQLInject = "mysql-inject"

func init() {
	executable, _ = os.Executable()
}

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	err = snapShot(c.db)
	if err != nil {
		return "", err
	}
	return c.f()
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLLock TODO
func NewMySQLLock(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLLock,
		f:    mysqlLock,
	}
}

// NewMySQLInject TODO
func NewMySQLInject(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLInject,
		f:    mysqlInject,
	}
}

// RegisterMySQLLock TODO
func RegisterMySQLLock() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLLock, NewMySQLLock
}

// RegisterMySQLInject TODO
func RegisterMySQLInject() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLInject, NewMySQLInject
}
