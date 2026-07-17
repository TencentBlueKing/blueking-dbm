// Package monitoriteminterface 监控项接口
package monitoriteminterface

import "dbm-services/mysql/db-tools/mysql-monitor/pkg"

// MonitorItemInterface TODO
type MonitorItemInterface interface {
	Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error)
	Name() string
}

// MonitorItemConstructorFuncType TODO
type MonitorItemConstructorFuncType func(cc *ConnectionCollect) MonitorItemInterface
