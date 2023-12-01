package timezonechange

import (
	"os"
	"path/filepath"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var nameSysTz = "sys-timezone-change"
var nameMySQLTz = "mysql-timezone-change"

type Checker struct {
	db   *sqlx.DB
	f    func(*sqlx.DB) (string, error)
	name string
}

var executable string
var contextBase string

func init() {
	executable, _ = os.Executable()
	contextBase = filepath.Join(filepath.Dir(executable), "context")
	_ = os.MkdirAll(contextBase, 0755)
}

func (c *Checker) Run() (msg string, err error) {
	return c.f(c.db)
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
