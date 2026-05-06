package spiderctlchecker

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
	"fmt"
	"log/slog"
	"strconv"

	"github.com/jmoiron/sqlx"
)

var getCtlPrimaryCheckerName = "get-ctl-primary"

type GetCtlPrimaryChecker struct {
	db *sqlx.DB
}

type primaryDesc struct {
	ServerName   string `db:"SERVER_NAME"`
	Host         string `db:"HOST"`
	Port         uint32 `db:"PORT"`
	IsThisServer uint32 `db:"IS_THIS_SERVER"`
}

func (c *GetCtlPrimaryChecker) Run() (msg string, err error) {
	_, err = c.getPrimary()
	if err != nil {
		slog.Error("Get primary checker error", slog.String("err", err.Error()))

		utils.SendMonitorEvent(
			getCtlPrimaryCheckerName,
			fmt.Sprintf("get primary failed: %s", err.Error()),
			map[string]interface{}{
				"instance_port": strconv.Itoa(config.MonitorConfig.Port + 1000),
			},
		)
	}
	return "", nil
}

func (c *GetCtlPrimaryChecker) getPrimary() (*primaryDesc, error) {
	res := primaryDesc{}
	err := c.db.QueryRowx(`tdbctl get primary`).StructScan(&res)
	if err != nil {
		return nil, err
	}

	return &res, nil
}

func (c *GetCtlPrimaryChecker) Name() string {
	return getCtlPrimaryCheckerName
}

func NewGetCtlPrimaryChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &GetCtlPrimaryChecker{db: cc.CtlDB}
}

func GetCtlPrimaryRegister() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return getCtlPrimaryCheckerName, NewGetCtlPrimaryChecker
}
