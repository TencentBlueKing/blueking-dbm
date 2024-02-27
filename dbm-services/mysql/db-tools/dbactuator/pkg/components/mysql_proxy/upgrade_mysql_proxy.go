/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql_proxy

import (
	"fmt"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
)

// UpgradeProxyComp TODO
type UpgradeProxyComp struct {
	GeneralParam *components.GeneralParam
	Params       *UpgradeProxyParam
	upgradeProxyRuntime
}

// UpgradeProxyParam MySQL proxy upgrade param
type UpgradeProxyParam struct {
	Host  string `json:"host" validate:"required,ip" ` // 当前实例的主机地址
	Ports []Port `json:"ports" validate:"required"`    // 当前实例的端口
	Force bool   `json:"force"`                        // 是否强制升级
	components.Medium
}

type upgradeProxyRuntime struct {
	adminUser       string
	adminPwd        string
	sysUsers        []string
	proxyAdminConns map[Port]*native.ProxyAdminDbWork
	proxyBackend    map[Port]string
	installPath     string
}

// Example subcommand example input
func (p *UpgradeProxyComp) Example() interface{} {
	comp := UpgradeProxyComp{
		Params: &UpgradeProxyParam{
			Host:  "127.0.0.1",
			Ports: []int{10000, 10001},
			Force: false,
			Medium: components.Medium{
				Pkg:    "mysql-proxy-0.82.13.tar.gz",
				PkgMd5: "xxx",
			},
		},
	}
	return comp
}

// Init prepare run env
func (p *UpgradeProxyComp) Init() (err error) {
	p.adminUser = p.GeneralParam.RuntimeAccountParam.ProxyAdminUser
	p.adminPwd = p.GeneralParam.RuntimeAccountParam.ProxyAdminPwd
	p.proxyAdminConns = make(map[Port]*native.ProxyAdminDbWork)
	p.proxyBackend = make(map[Port]string)
	p.installPath = cst.UsrLocal
	if err = p.connAllProxyAdminPorts(); err != nil {
		return err
	}
	p.sysUsers = p.GeneralParam.GetAllSysAccount()
	p.sysUsers = append(p.sysUsers, "system", "root", "unauthenticated user", "ADMIN")
	return nil
}

func (p *UpgradeProxyComp) connAllProxyAdminPorts() (err error) {
	for _, port := range p.Params.Ports {
		conn, err := native.InsObject{
			Port: port,
			Host: p.Params.Host,
			User: p.adminUser,
			Pwd:  p.adminPwd,
		}.ConnProxyAdmin()
		if err != nil {
			logger.Error("connect proxy %d admin port failed %s", port, err.Error())
			return err
		}
		p.proxyAdminConns[port] = conn
		backend, err := conn.SelectBackend()
		if err != nil {
			logger.Error("select backends info failed %s", err.Error())
			return err
		}
		p.proxyBackend[port] = backend.Address
	}
	return nil
}

// PreCheck pre run pre check
func (p *UpgradeProxyComp) PreCheck() (err error) {
	if err = p.Params.Medium.Check(); err != nil {
		return err
	}
	if !p.Params.Force {
		return p.checkAppProcessist()
	}
	return nil
}

func (p *UpgradeProxyComp) checkAppProcessist() (err error) {
	for port, adminConn := range p.proxyAdminConns {
		activeprocesslist, err := adminConn.ShowAppProcesslists(p.sysUsers)
		if err != nil {
			logger.Error("get %d processlist failed %v", port, err)
			return err
		}
		if len(activeprocesslist) > 0 {
			errMsg := fmt.Sprintf("还存在活跃的业务连接,请先确认,具体连接%v", activeprocesslist)
			logger.Error(errMsg)
			return fmt.Errorf(errMsg)
		}
	}
	return nil
}

// ReplaceMedium 替换介质
func (p *UpgradeProxyComp) ReplaceMedium() (err error) {
	logger.Info("解压新版的介质")
	pkgAbPath := p.Params.Medium.GetAbsolutePath()
	if output, err := osutil.StandardShellCommand(false, fmt.Sprintf("cd %s && tar zxf %s -C ./ ", p.installPath,
		pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	logger.Info("更改mysql-proxy的软连接指向新的版本")
	replaceCmd := fmt.Sprintf("cd %s && unlink %s && ln -s %s %s", p.installPath, cst.ProxyInstallPath,
		p.Params.GePkgBaseName(),
		cst.ProxyInstallPath)
	logger.Info("替换命令 %s", replaceCmd)
	if output, err := osutil.StandardShellCommand(false, replaceCmd); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	return nil
}

// RestartProxy TODO
func (p *UpgradeProxyComp) RestartProxy() (err error) {
	for _, port := range p.Params.Ports {
		err = proxyutil.StartProxyParam{
			InstallPath:    cst.ProxyInstallPath,
			ProxyCnf:       util.GetProxyCnfName(port),
			Host:           p.Params.Host,
			Port:           port,
			ProxyAdminUser: p.adminUser,
			ProxyAdminPwd:  p.adminPwd,
		}.Restart()
		if err != nil {
			logger.Error("restart mysql proxy %d failed %s", port, err.Error())
			return err
		}
	}
	return nil
}

// RefreshBackends The reason for needing to refresh backends is that,
// on old mysql-proxy instances, the backends info might differ from what's in the proxy.cnf file
// In this case, after a new mysql-proxy instance is started, it might get the wrong backends from the cnf file.
// Therefore, we stored the latest backends info from old proxies by "SELECT * FROM backends" in Init(),
// then we use it to refresh the new proxy for service consistence.
func (p *UpgradeProxyComp) RefreshBackends() (err error) {
	// 重新连接proxy
	if err = p.connAllProxyAdminPorts(); err != nil {
		logger.Error("重新连接proxy失败%v", err)
		return err
	}
	for port, conn := range p.proxyAdminConns {
		ver, err := conn.SelectVersion()
		if err != nil {
			return err
		}
		logger.Info("after upgrade,current proxy %d: version:%s", port, ver)
		backendAddr := p.proxyBackend[port]
		if cmutil.IsEmpty(backendAddr) {
			logger.Warn("the %d backend is empty", port)
			continue
		}
		if _, err = conn.Exec(fmt.Sprintf("refresh_backends('%s',1)", backendAddr)); err != nil {
			logger.Error("refresh backends failed %s", err.Error())
			return err
		}
	}
	return nil
}
