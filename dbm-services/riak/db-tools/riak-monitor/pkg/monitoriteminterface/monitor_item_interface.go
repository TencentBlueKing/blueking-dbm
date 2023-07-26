// Package monitoriteminterface 监控项接口
package monitoriteminterface

// MonitorItemInterface TODO
type MonitorItemInterface interface {
	Run() (msg string, err error)
	Name() string
}

// MonitorItemConstructorFuncType TODO
type MonitorItemConstructorFuncType func(cc *ConnectionCollect) MonitorItemInterface
