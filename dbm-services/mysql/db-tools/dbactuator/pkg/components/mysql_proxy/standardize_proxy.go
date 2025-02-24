package mysql_proxy

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

type StandardizeProxyComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *StandardizeProxyParam   `json:"extend"`
}

type StandardizeProxyParam struct {
	DBHAAccount string `json:"dbha_account"`
	IP          string `json:"ip"`
	PortList    []int  `json:"port_list"`
}

func (c *StandardizeProxyComp) ClearOldCrontab() error {
	err := osutil.CleanLocalCrontab()
	if err != nil {
		logger.Error("clear mysql crontab failed: %s", err.Error())
		return err
	} else {
		logger.Info("clear mysql crontab success")
	}
	return nil
}

func (c *StandardizeProxyComp) AddUser() error {
	for _, port := range c.Params.PortList {
		err := c.addOnePort(port)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *StandardizeProxyComp) addOnePort(port int) error {
	pc, err := native.NewDbWorkerNoPing(
		fmt.Sprintf(`%s:%d`, c.Params.IP, native.GetProxyAdminPort(port)),
		c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		c.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	defer func() {
		pc.Stop()
	}()

	_, err = pc.Exec(fmt.Sprintf(`refresh_users('%s@%%', '+')`, c.Params.DBHAAccount))
	if err != nil {
		logger.Error("add dbha account failed %s", err.Error())
		return err
	}

	return nil
}

func (c *StandardizeProxyComp) Example() interface{} {
	return StandardizeProxyComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &StandardizeProxyParam{
			DBHAAccount: "dbha_account",
			IP:          "127.0.0.1",
			PortList:    []int{1, 2, 3},
		},
	}
}
