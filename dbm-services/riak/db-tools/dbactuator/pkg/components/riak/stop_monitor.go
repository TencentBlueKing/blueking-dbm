// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import "dbm-services/common/go-pubpkg/logger"

// StopMonitorComp TODO
type StopMonitorComp struct {
	Params                *StopMonitorParam `json:"extend"`
	StopMonitorRunTimeCtx `json:"-"`
}

// StopMonitorParam TODO
type StopMonitorParam struct {
}

// StopMonitorRunTimeCtx 运行时上下文
type StopMonitorRunTimeCtx struct {
}

// StopMonitor 关闭监控
func (i *StopMonitorComp) StopMonitor() error {
	// 退出mysql-crond
	err := QuitCrond()
	if err != nil {
		logger.Error("quit crond error: %s", err.Error())
		return err
	}
	logger.Info("quit crond success")
	return nil
}
