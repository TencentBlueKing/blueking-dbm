package checkload

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
	"fmt"

	"github.com/pkg/errors"
)

var NameCheckLoadHealth = "riak-load-health"

func init() {}

// Checker TODO
type Checker struct {
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	msg, err = c.f()
	if err != nil {
		return "", errors.Wrap(err, fmt.Sprintf("run %s", c.name))
	}
	return msg, nil
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewCheckLoadHealth TODO
func NewCheckLoadHealth(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		name: NameCheckLoadHealth,
		f:    CheckResponseTime,
	}
}

// RegisterCheckLoadHealth TODO
func RegisterCheckLoadHealth() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return NameCheckLoadHealth, NewCheckLoadHealth
}
