package connections

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
	"fmt"

	"github.com/pkg/errors"
)

// NameConnections 检查riak连接数监控名称
var NameConnections = "riak_connections_heart_beat"

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

// Name 监控名称
func (c *Checker) Name() string {
	return c.name
}

// NewConnections 查看连接
func NewConnections(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		name: NameConnections,
		f:    Connections,
	}
}

// RegisterConnections 注册查看连接
func RegisterConnections() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return NameConnections, NewConnections
}
