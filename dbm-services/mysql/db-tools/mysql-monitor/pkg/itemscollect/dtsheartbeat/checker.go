// Package dtsheartbeat 上报 DTS 进程存活与采集心跳。
package dtsheartbeat

import (
	"net"
	"strconv"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
)

const name = "dts-heartbeat"

const (
	metricHeartBeat = "dts_monitor_heart_beat"
	metricProcessUp = "dts_process_up"
	probeTimeout    = 800 * time.Millisecond
)

type Checker struct{}

func ProbeAddr(ip string, port int) bool {
	if ip == "" || port <= 0 {
		return false
	}
	addr := net.JoinHostPort(ip, strconv.Itoa(port))
	conn, err := net.DialTimeout("tcp", addr, probeTimeout)
	if err != nil {
		return false
	}
	_ = conn.Close()
	return true
}

func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	ip, port := "", 0
	if config.MonitorConfig != nil {
		ip = config.MonitorConfig.Ip
		port = config.MonitorConfig.Port
	}
	up := int64(0)
	if ProbeAddr(ip, port) {
		up = 1
	}
	utils.SendMonitorMetrics(metricProcessUp, up, nil)
	utils.SendMonitorMetrics(metricHeartBeat, 1, nil)
	return nil, "", nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(_ *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}
