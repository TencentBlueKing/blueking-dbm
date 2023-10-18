// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

// StartMonitorComp TODO
type StartMonitorComp struct {
	Params                 *StartMonitorParam `json:"extend"`
	StartMonitorRunTimeCtx `json:"-"`
}

// StartMonitorParam TODO
type StartMonitorParam struct {
}

// StartMonitorRunTimeCtx 运行时上下文
type StartMonitorRunTimeCtx struct {
}

// StartMonitor 启动监控
func (i *StartMonitorComp) StartMonitor() error {
	var deploy *DeployMonitorComp
	return deploy.DeployMonitor()
}
