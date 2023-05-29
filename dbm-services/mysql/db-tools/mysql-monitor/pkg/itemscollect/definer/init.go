package definer

import (
	"fmt"
	"strings"
	"sync"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var nameRoutine = "routine-definer"
var nameView = "view-definer"
var nameTrigger = "trigger-definer"

var mysqlUsers []string

var snapErr error
var once sync.Once

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func(*sqlx.DB) ([]string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	once.Do(func() {
		snapErr = snapshot(c.db)
	})
	if snapErr != nil {
		return "", snapErr
	}

	msgSlice, err := c.f(c.db)
	if err != nil {
		return "", errors.Wrap(err, fmt.Sprintf("run %s", c.name))
	}

	return strings.Join(msgSlice, ". "), nil
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
