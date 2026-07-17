package definer

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"strings"
	"sync"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var nameRoutine = "routine-definer"
var nameView = "view-definer"
var nameTrigger = "trigger-definer"

var mysqlUsers []string

var snapErr error
var once sync.Once

// Checker TODO
type Checker struct {
	db   *pkg.MySQLMonitorDBH
	name string
	f    func(dbh *pkg.MySQLMonitorDBH) ([]string, error)
}

// Run TODO
func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	once.Do(func() {
		snapErr = snapshot(c.db)
	})
	if snapErr != nil {
		return nil, "", snapErr
	}

	msgSlice, err := c.f(c.db)
	if err != nil {
		return nil, "", err
	}

	return nil, strings.Join(msgSlice, ". "), nil
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewCheckRoutineDefiner TODO
func NewCheckRoutineDefiner(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameRoutine,
		f:    routines,
	}
}

// NewCheckViewDefiner TODO
func NewCheckViewDefiner(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameView,
		f:    views,
	}
}

// NewCheckTriggerDefiner TODO
func NewCheckTriggerDefiner(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameTrigger,
		f:    triggers,
	}
}

// RegisterCheckRoutineDefiner TODO
func RegisterCheckRoutineDefiner() (
	string,
	monitoriteminterface.MonitorItemConstructorFuncType,
) {
	return nameRoutine, NewCheckRoutineDefiner
}

// RegisterCheckViewDefiner TODO
func RegisterCheckViewDefiner() (
	string,
	monitoriteminterface.MonitorItemConstructorFuncType,
) {
	return nameView, NewCheckViewDefiner
}

// RegisterCheckTriggerDefiner TODO
func RegisterCheckTriggerDefiner() (
	string,
	monitoriteminterface.MonitorItemConstructorFuncType,
) {
	return nameTrigger, NewCheckTriggerDefiner
}
