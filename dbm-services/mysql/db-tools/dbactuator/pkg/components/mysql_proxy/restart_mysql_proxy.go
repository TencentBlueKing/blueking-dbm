package mysql_proxy

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
)

// RestartMySQLProxyComp TODO
type RestartMySQLProxyComp struct {
	GeneralParam *components.GeneralParam
	Params       *RestartMySQLProxyParam
}

// RestartMySQLProxyParam TODO
type RestartMySQLProxyParam struct {
	Host string `json:"host"  validate:"required,ip"`
	Port int    `json:"port"  validate:"required,gte=3306"` // 被重启的proxy端口
}

// Example TODO
func (u *RestartMySQLProxyComp) Example() interface{} {
	comp := RestartMySQLProxyComp{
		Params: &RestartMySQLProxyParam{
			Host: "1.1.1.1",
			Port: 10000,
		},
	}
	return comp
}

// PreCheck 提前检查下proxy client 等情况, 这里不检查proxy是否连接
//
//	@receiver u
//	@return err
func (u *RestartMySQLProxyComp) PreCheck() (err error) {

	db := native.InsObject{
		Host: u.Params.Host,
		User: u.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  u.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
		Port: u.Params.Port,
	}
	_, err = db.ConnProxyAdmin()
	if err != nil {
		logger.Error("连接%d的Admin Port 失败%s", u.Params.Port, err.Error())
		return err
	}
	// inuse, err := db.CheckProxyInUse()
	// if err != nil {
	// 	logger.Error("检查Proxy可用性检查失败")
	// 	return err
	// }
	// if inuse {
	// 	return fmt.Errorf("检测到%d存在可用连接", u.Params.Port)
	// }

	return
}

// RestartProxy TODO
// UnInstallProxy 停止Proxy 然后在备份目录
//
//	@receiver u
//	@return err
func (u *RestartMySQLProxyComp) RestartProxy() (err error) {

	// 先正常关闭proxy进程
	if err = proxyutil.KillDownProxy(u.Params.Port); err != nil {
		logger.Error("停止%d进程失败:%s", u.Params.Port, err.Error())
		return err
	}
	logger.Info("关闭 proxy(%d) 成功", u.Params.Port)

	// 然后启动proxy进程
	p := proxyutil.StartProxyParam{
		InstallPath: cst.ProxyInstallPath,
		ProxyCnf:    util.GetProxyCnfName(u.Params.Port),
		Host:        u.Params.Host,
		Port:        getAdminPort(u.Params.Port), // Is Admin Port
		ProxyUser:   u.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		ProxyPwd:    u.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}
	if err := p.Start(); err != nil {
		logger.Error("启动 proxy(%d) 失败,err:%s", u.Params.Port, err.Error())
		return err
	}
	logger.Info("启动 proxy(%d) 成功", u.Params.Port)

	return nil
}
