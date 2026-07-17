package timezonechange

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var nameSysTz = "sys-timezone-change"
var nameMySQLTz = "mysql-timezone-change"

type Checker struct {
	db   *pkg.MySQLMonitorDBH
	f    func(dbh *pkg.MySQLMonitorDBH) (string, error)
	name string
}

var executable string
var contextBase string

func init() {
	executable, _ = os.Executable()
	contextBase = filepath.Join(filepath.Dir(executable), "context")
	_ = os.MkdirAll(contextBase, 0755)
}

func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	msg, err = c.f(c.db)
	return nil, msg, err
}

func (c *Checker) Name() string {
	return c.name
}

func NewCheckSysTimezoneChange(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSysTz,
		f:    sysTzChange,
	}
}

func RegisterSysTimezoneChange() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameSysTz, NewCheckSysTimezoneChange
}

func NewCheckMySQLTimezoneChange(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLTz,
		f:    mysqlTzChange,
	}
}

func RegisterMySQLTimezoneChange() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLTz, NewCheckMySQLTimezoneChange
}
