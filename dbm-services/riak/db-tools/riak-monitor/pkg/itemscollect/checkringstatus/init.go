package checkringstatus

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
	"fmt"

	"github.com/pkg/errors"
)

var NameCheckRingStatus = "riak-ring-status"

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

// NewCheckRingStatus TODO
func NewCheckRingStatus(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		name: NameCheckRingStatus,
		f:    CheckRingStatus,
	}
}

// RegisterCheckRingStatus TODO
func RegisterCheckRingStatus() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return NameCheckRingStatus, NewCheckRingStatus
}
