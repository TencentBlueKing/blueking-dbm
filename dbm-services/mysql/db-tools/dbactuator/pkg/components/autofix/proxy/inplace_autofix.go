package proxy

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
)

type InplaceAutofixParams struct {
	Host           string `json:"host" validate:"required,ip"`
	Port           int    `json:"port" validate:"required"`
	BackendHost    string `json:"backend-host" validate:"required,ip"`
	BackendPort    int    `json:"backend-port" validate:"required,gte=3306"`
	AliveProxyHost string `json:"alive-proxy-host" validate:"required,ip"`
	AliveProxyPort int    `json:"alive-proxy-port" validate:"required,gte=3306"`
}

type InplaceAutofixComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       []*InplaceAutofixParams  `json:"extend"`

	cloneUsersComp []*mysql_proxy.CloneProxyUserComp
}

func (c *InplaceAutofixComp) Init() (err error) {
	for _, ele := range c.Params {
		c.cloneUsersComp = append(c.cloneUsersComp, &mysql_proxy.CloneProxyUserComp{
			GeneralParam: c.GeneralParam,
			Params: &mysql_proxy.CloneProxyUserParam{
				SourceProxyHost: ele.AliveProxyHost,
				SourceProxyPort: ele.AliveProxyPort,
				TargetProxyHost: ele.Host,
				TargetProxyPort: ele.Port,
			},
		})
	}

	return nil
}

func (c *InplaceAutofixComp) StartProxy() (err error) {
	for _, ele := range c.Params {
		_ = proxyutil.KillDownProxy(ele.Port)

		p := proxyutil.StartProxyParam{
			InstallPath:    cst.ProxyInstallPath,
			ProxyCnf:       util.GetProxyCnfName(ele.Port),
			Host:           ele.Host,
			Port:           ele.Port,
			ProxyAdminUser: c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
			ProxyAdminPwd:  c.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
		}

		err = p.Start(ele.Port)
		if err != nil {
			logger.Error("start proxy %d failed: %s", ele.Port, err)
			return err
		}
		logger.Info("start proxy %d success", ele.Port)
	}

	logger.Info("start proxy success")
	return nil
}

func (c *InplaceAutofixComp) CloneUsers() (err error) {
	for _, ele := range c.cloneUsersComp {
		err = ele.Init()
		if err != nil {
			logger.Error(
				"init clone users from %s to %s failed: %s",
				ele.SourceProxyAdminConn.Dsn,
				ele.TargetProxyAdminConn.Dsn,
				err,
			)
			return err
		}
		err = ele.CloneProxyUser()
		if err != nil {
			logger.Error(
				"clone proxy users from %s to %s failed: %s",
				ele.SourceProxyAdminConn.Dsn,
				ele.TargetProxyAdminConn.Dsn,
				err,
			)
			return err
		}

		logger.Info(
			"clone proxy users from %s to %s success",
			ele.SourceProxyAdminConn.Dsn,
			ele.TargetProxyAdminConn.Dsn,
		)
	}
	logger.Info("clone users success")
	return nil
}

func (c *InplaceAutofixComp) SetBackend() (err error) {
	for _, ele := range c.Params {
		pa, err := native.InsObject{
			Host: ele.Host,
			Port: ele.Port,
			User: c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
			Pwd:  c.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
		}.ConnProxyAdmin()
		if err != nil {
			logger.Error("conn proxy %d admin failed: %s", ele.Port, err)
			return err
		}

		err = pa.RefreshBackends(ele.BackendHost, ele.BackendPort)
		if err != nil {
			logger.Error(
				"refresh %d backend to %s:%d failed: %s",
				ele.Port, ele.BackendHost, ele.BackendPort, err,
			)
			return err
		}

		logger.Info(
			"refresh %d backend to %s:%d success",
			ele.Port, ele.BackendHost, ele.BackendPort,
		)
	}

	logger.Info("set backend success")
	return nil
}

func (c *InplaceAutofixComp) Example() interface{} {
	return &InplaceAutofixComp{
		Params: []*InplaceAutofixParams{
			{
				Host:           "127.0.0.1",
				Port:           20001,
				BackendHost:    "127.0.0.2",
				BackendPort:    3306,
				AliveProxyHost: "127.0.0.3",
				AliveProxyPort: 3306,
			},
		},
	}
}
