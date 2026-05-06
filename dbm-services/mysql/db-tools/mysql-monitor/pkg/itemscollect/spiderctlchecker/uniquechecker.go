package spiderctlchecker

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"log/slog"
	"math/big"
	"net"
	"strconv"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
)

/*
1. 每一个 spider master 上的中控节点都上报自己看到的 ctl master
2. 在监控平台做 count 计数, > 1 则告警
*/

var uniqueCheckerName = "unique-ctl-master"

type UniqueCtlChecker struct {
	//db *sqlx.DB
	GetCtlPrimaryChecker
}

func (c *UniqueCtlChecker) Run() (msg string, err error) {
	p, err := c.getPrimary()
	if err != nil {
		return "", err
	}

	slog.Info(
		"unique-ctl-master",
		slog.String("ctl master", p.Host),
	)

	ret := big.NewInt(0)
	ret.SetBytes(net.ParseIP(p.Host).To4())

	utils.SendMonitorMetrics(
		"unique_ctl_master",
		ret.Int64(),
		map[string]interface{}{
			"ctl-master":    p.Host,
			"instance_port": strconv.Itoa(config.MonitorConfig.Port + 1000), // 调整维度为 ctl 端口
		},
	)

	return "", nil
}

func (c *UniqueCtlChecker) Name() string {
	return uniqueCheckerName
}

func NewUniqueCtlChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &UniqueCtlChecker{GetCtlPrimaryChecker{db: cc.CtlDB}}
}

func UniqueCtlCheckerRegister() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return uniqueCheckerName, NewUniqueCtlChecker
}
