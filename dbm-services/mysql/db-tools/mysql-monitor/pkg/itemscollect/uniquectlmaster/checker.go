package uniquectlmaster

import (
	"log/slog"
	"math/big"
	"net"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
)

/*
1. 每一个 spider master 上的中控节点都上报自己看到的 ctl master
2. 在监控平台做 count 计数, > 1 则告警
*/

var name = "unique-ctl-master"

type Checker struct {
	db *sqlx.DB
}

func (c *Checker) Run() (msg string, err error) {
	var res struct {
		ServerName   string `db:"SERVER_NAME"`
		Host         string `db:"HOST"`
		Port         uint32 `db:"PORT"`
		IsThisServer uint32 `db:"IS_THIS_SERVER"`
	}
	err = c.db.QueryRowx(`tdbctl get primary`).StructScan(&res)
	if err != nil {
		return "", err
	}

	slog.Info("unique-ctl-master",
		slog.String("ctl master", res.Host))

	ret := big.NewInt(0)
	ret.SetBytes(net.ParseIP(res.Host).To4())

	utils.SendMonitorMetrics(
		"unique_ctl_master",
		ret.Int64(),
		map[string]interface{}{
			"ctl-master": res.Host,
		},
	)

	return "", nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{db: cc.CtlDB}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}
