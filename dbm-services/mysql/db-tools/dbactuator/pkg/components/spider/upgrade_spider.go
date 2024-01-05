/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spider

import (
	"fmt"
	"path"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// UpgradeSpiderComp TODO
type UpgradeSpiderComp struct {
	GeneralParam *components.GeneralParam
	Param        *UpgradeSpiderParam
	upgradeSpiderRuntime
}

// Port TODO
type Port = int

// UpgradeSpiderParam TODO
type UpgradeSpiderParam struct {
	Host  string `json:"host" validate:"required,ip" ` // 当前实例的主机地址
	Ports []Port `json:"ports" validate:"required"`    // 当前实例的端口
	Force bool   `json:"force"`                        // 是否强制升级
	components.Medium
}
type upgradeSpiderRuntime struct {
	adminUser   string
	adminPwd    string
	sysUsers    []string
	spiderIns   map[Port]native.InsObject
	spiderConns map[Port]*native.DbWorker
	socketMaps  map[Port]string
	installPath string
}

// Example subcommand example input
func (i *UpgradeSpiderComp) Example() interface{} {
	return UpgradeSpiderComp{
		Param: &UpgradeSpiderParam{
			Host:  "127.0.0.1",
			Ports: []int{25000, 25001},
			Force: false,
			Medium: components.Medium{
				Pkg:    "mariadb-10.3.7-linux-x86_64-tspider-3.7.8-gcs.tar.gz",
				PkgMd5: "xxx",
			},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
			RuntimeExtend: components.RuntimeExtend{
				MySQLSysUsers: []string{"root", "system user"},
			},
		},
	}
}

// Init prepare run env
func (i *UpgradeSpiderComp) Init() (err error) {
	i.adminUser = i.GeneralParam.RuntimeAccountParam.AdminUser
	i.adminPwd = i.GeneralParam.RuntimeAccountParam.AdminPwd
	i.spiderIns = make(map[int]native.InsObject)
	i.spiderConns = make(map[int]*native.DbWorker)
	i.sysUsers = i.GeneralParam.GetAllSysAccount()
	i.socketMaps = make(map[int]string)
	for _, port := range i.Param.Ports {
		conn, err := native.InsObject{
			Host: i.Param.Host,
			Port: port,
			User: i.adminUser,
			Pwd:  i.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("connect spider %d failed,err:%s", port, err.Error())
			return err
		}
		socket, err := conn.ShowSocket()
		if err != nil {
			logger.Error("get %d socket from show variables failed %s", port, err.Error())
			return err
		}
		i.spiderConns[port] = conn
		i.spiderIns[port] = native.InsObject{
			Host:   i.Param.Host,
			Port:   port,
			User:   i.adminUser,
			Pwd:    i.adminPwd,
			Socket: socket,
		}
	}
	return nil
}

// PreCheck pre run pre check
func (i *UpgradeSpiderComp) PreCheck() (err error) {
	if i.Param.Force {
		return nil
	}
	var version string
	for port, conn := range i.spiderConns {
		activeprocesslist, err := conn.ShowApplicationProcesslist(i.sysUsers)
		if err != nil {
			logger.Error("get %d processlist failed %v", port, err)
			return err
		}
		if len(activeprocesslist) > 0 {
			errMsg := fmt.Sprintf("还存在活跃的业务连接,请先确认,具体连接%v", activeprocesslist)
			logger.Error(errMsg)
			return fmt.Errorf(errMsg)
		}
		version, err = conn.SelectVersion()
		if err != nil {
			logger.Error("get %d version failed %s", port, err.Error())
			return err
		}
	}
	pkgBaseName := i.Param.GePkgBaseName()
	logger.Info("current version is %s", version)
	logger.Info("the new version is %s", pkgBaseName)
	currentVernum := cmutil.SpiderVersionParse(version)
	newVernum := cmutil.SpiderVersionParse(pkgBaseName)
	if currentVernum > newVernum {
		return fmt.Errorf("the new version is Lower Than Current version")
	}
	if currentVernum < cmutil.SpiderVersionParse("tspider-3.0") && newVernum >= cmutil.SpiderVersionParse("tspider-3.0") {
		return fmt.Errorf(
			"direct upgrades across major versions are not allowed,example not allowed tspider1.x upgrade tspider3.x")
	}
	return nil
}

// CreateSpiderTable 初始化新版本的spider初始化sql
func (i *UpgradeSpiderComp) CreateSpiderTable() (err error) {
	for port, socket := range i.socketMaps {
		err = mysqlutil.ExecuteSqlAtLocal{
			User:     i.adminUser,
			Password: i.adminPwd,
			Socket:   socket,
		}.ExcuteSqlByMySQLClientOne(path.Join(cst.MysqldInstallPath, "scripts/install_spider.sql"), "")
		if err != nil {
			logger.Error("%d excute create spider table failed: %s", port, err.Error())
			return err
		}
	}
	return err
}

// ReplaceMedium 替换新版的介质
func (i *UpgradeSpiderComp) ReplaceMedium() (err error) {
	pkgAbPath := i.Param.GetAbsolutePath()
	if output, err := osutil.StandardShellCommand(false, fmt.Sprintf("cd %s && tar zxf %s -C ./ ", cst.UsrLocal,
		pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	logger.Info("update spider soft link to new version")
	replaceCmd := fmt.Sprintf("cd %s && unlink %s && ln -s %s %s",
		cst.UsrLocal,
		cst.MysqldInstallPath,
		i.Param.GePkgBaseName(),
		cst.MysqldInstallPath)
	logger.Info("relink command: %s", replaceCmd)
	if output, err := osutil.StandardShellCommand(false, replaceCmd); err != nil {
		logger.Error("relink new verion %s failed, error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	return nil
}

// Restart restart all spider instance
func (i *UpgradeSpiderComp) Restart() (err error) {
	for port, ins := range i.spiderIns {
		logger.Info("start retsart %d", port)
		if err = computil.RestartMysqlInstanceNormal(ins); err != nil {
			logger.Error("retsart spider instance  %d failed %s", port, err.Error())
			return err
		}
	}
	logger.Info("restart all spider successfully ~")
	return nil
}
