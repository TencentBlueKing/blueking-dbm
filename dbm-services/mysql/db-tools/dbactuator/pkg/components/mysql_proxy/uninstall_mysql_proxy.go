package mysql_proxy

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
	"fmt"
	"path"
	"strconv"
	"strings"
)

// UnInstallMySQLProxyComp TODO
type UnInstallMySQLProxyComp struct {
	GeneralParam *components.GeneralParam
	Params       *UnInstallMySQLProxyParam
	runTimeCtx
}

// UnInstallMySQLProxyParam TODO
type UnInstallMySQLProxyParam struct {
	Host  string `json:"host"  validate:"required,ip"`
	Force bool   `json:"force"`                                // 是否强制下架
	Ports []int  `json:"ports"  validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口
}

// 运行是需要的必须参数,可以提前计算
type runTimeCtx struct {
	proxyAdminUser string
	proxyAdminPwd  string
	proxyInsLogDir map[Port]string // 每个proxy实例的日志目录
}

// Init 初始化组件运行参数
//
//	@receiver u
//	@return err
func (u *UnInstallMySQLProxyComp) Init() (err error) {
	u.runTimeCtx.proxyAdminUser = u.GeneralParam.RuntimeAccountParam.ProxyAdminUser
	u.runTimeCtx.proxyAdminPwd = u.GeneralParam.RuntimeAccountParam.ProxyAdminPwd
	u.runTimeCtx.proxyInsLogDir = make(map[int]string)
	for _, port := range u.Params.Ports {
		proxyCnf := util.GetProxyCnfName(port)
		if !cmutil.FileExists(proxyCnf) {
			return fmt.Errorf("%s不存在", proxyCnf)
		}
		f, err := util.LoadMyCnfForFile(proxyCnf)
		if err != nil {
			logger.Error("加载%s配置失败%s", proxyCnf, err)
			return err
		}
		// example logfile value: /data/mysql-proxy/10000/log/mysql-proxy.log
		var logfile string
		if logfile, err = f.GetProxyLogFilePath(); err != nil {
			return err
		}
		sl := strings.Split(logfile, strconv.Itoa(port))
		if len(sl) < 2 {
			return fmt.Errorf("proxy logfile 可能格式不对:%s", logfile)
		}
		// /data/mysql-proxy/10000
		u.runTimeCtx.proxyInsLogDir[port] = path.Join(sl[0], strconv.Itoa(port))
	}
	return
}

// PreCheck  如果非强制下架。提前检查下proxy client 等情况
//
//	@receiver u
//	@return err
func (u *UnInstallMySQLProxyComp) PreCheck() (err error) {
	for _, port := range u.Params.Ports {
		if !u.Params.Force {
			db, err := native.InsObject{
				Host: u.Params.Host,
				User: u.runTimeCtx.proxyAdminUser,
				Pwd:  u.proxyAdminPwd,
				Port: port,
			}.ConnProxyAdmin()
			if err != nil {
				logger.Error("连接%d的Admin Port 失败%s", port, err.Error())
				return err
			}
			inuse, err := db.CheckProxyInUse()
			if err != nil {
				logger.Error("检查Proxy可用性检查失败")
				return err
			}
			if inuse {
				return fmt.Errorf("检测到%d存在可用连接", port)
			}
		}
		continue
	}
	return err
}

// CleanCrontab  先注释掉Crontab 相关的计划，包括告警,以免下架告警
//  @receiver u
//  @return err
// func (u *UnInstallMySQLProxyComp) CleanCrontab() (err error) {
// 	logger.Info("开始清理机器上的crontab")
// 	if err = osutil.CleanLocalCrontab(); err != nil {
// 		return err
// 	}
// 	return
// }

// UnInstallProxy 停止Proxy 然后在备份目录
//
//	@receiver u
//	@return err
func (u *UnInstallMySQLProxyComp) UnInstallProxy() (err error) {
	for _, port := range u.Params.Ports {
		if err = proxyutil.KillDownProxy(port); err != nil {
			logger.Error("停止%d进程失败:%s", port, err.Error())
			return err
		}
		if err = osutil.SafeRmDir(u.runTimeCtx.proxyInsLogDir[port]); err != nil {
			logger.Error("删除log dir失败:%s", u.runTimeCtx.proxyInsLogDir[port])
			return err
		}
	}
	return nil
}
