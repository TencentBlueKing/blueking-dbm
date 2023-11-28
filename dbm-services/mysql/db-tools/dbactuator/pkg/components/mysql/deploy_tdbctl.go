/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"encoding/json"
	"fmt"
	"path"
	"regexp"
	"strconv"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// InitTdbctlDeploy TODO
func (i *InstallMySQLComp) InitTdbctlDeploy() (err error) {
	i.WorkUser = "root"
	i.WorkPassword = ""
	i.InstallDir = cst.UsrLocal
	i.MysqlInstallDir = cst.MysqldInstallPath
	i.TdbctlInstallDir = cst.TdbctlInstallPath
	i.DataRootPath = cst.DefaultMysqlDataRootPath
	i.LogRootPath = cst.DefaultMysqlLogRootPath
	i.DefaultMysqlDataDirName = cst.DefaultMysqlDataBasePath
	i.DefaultMysqlLogDirName = cst.DefaultMysqlLogBasePath
	// 计算获取需要安装的ports
	i.InsPorts = i.Params.Ports
	i.MyCnfTpls = make(map[int]*util.CnfFile)
	var mountpoint string
	if mountpoint, err = osutil.FindFirstMountPointProxy(
		cst.DefaultProxyDataRootPath,
		cst.AlterNativeProxyDataRootPath,
	); err != nil {
		logger.Error("not found mount point /data1")
		return err
	}
	i.DataRootPath = mountpoint
	i.DataBaseDir = path.Join(mountpoint, cst.DefaultMysqlDataBasePath)
	i.LogRootPath = mountpoint
	i.LogBaseDir = path.Join(mountpoint, cst.DefaultMysqlLogBasePath)

	// 反序列化mycnf 配置
	var mycnfs map[Port]json.RawMessage
	if err = json.Unmarshal([]byte(i.Params.MyCnfConfigs), &mycnfs); err != nil {
		logger.Error("反序列化配置失败:%s", err.Error())
		return err
	}
	for _, port := range i.InsPorts {
		var cnfraw json.RawMessage
		var ok bool
		if cnfraw, ok = mycnfs[port]; !ok {
			return fmt.Errorf("参数中没有%d的配置", port)
		}
		var mycnf mysqlutil.MycnfObject
		if err = json.Unmarshal(cnfraw, &mycnf); err != nil {
			logger.Error("反序列%d 化配置失败:%s", port, err.Error())
			return err
		}
		cnftpl, err := util.NewMyCnfObject(mycnf, "tpl")
		if err != nil {
			logger.Error("初始化mycnf ini 模版:%s", err.Error())
			return err
		}
		//  删除 innodb 相关配置参数
		innodbRe := regexp.MustCompile("^innodb")
		for _, item := range cnftpl.Cfg.Section(util.MysqldSec).Keys() {
			if innodbRe.MatchString(item.Name()) {
				cnftpl.Cfg.Section(util.MysqldSec).DeleteKey(item.Name())
			}
		}
		i.MyCnfTpls[port] = cnftpl
	}
	// 计算需要替换的参数配置
	if err := i.replacecnf(); err != nil {
		return err
	}
	i.Checkfunc = append(i.Checkfunc, i.CheckTimeZoneSetting)
	i.Checkfunc = append(i.Checkfunc, i.precheckMysqlPackageBitOS)
	i.Checkfunc = append(i.Checkfunc, i.Params.Medium.Check)
	return nil
}

func (i *InstallMySQLComp) replacecnf() error {
	i.RenderConfigs = make(map[int]RenderConfigs)
	i.InsInitDirs = make(map[int]InitDirs)
	i.InsSockets = make(map[int]string)
	for _, port := range i.InsPorts {
		insBaseDataDir := path.Join(i.DataBaseDir, strconv.Itoa(port))
		insBaseLogDir := path.Join(i.LogBaseDir, strconv.Itoa(port))
		serverId, err := mysqlutil.GenMysqlServerId(i.Params.Host, port)
		if err != nil {
			logger.Error("%s:%d generation serverId Failed %s", i.Params.Host, port, err.Error())
			return err
		}
		i.RenderConfigs[port] = RenderConfigs{Mysqld{
			Datadir:            insBaseDataDir,
			Logdir:             insBaseLogDir,
			ServerId:           serverId,
			Port:               strconv.Itoa(port),
			CharacterSetServer: i.Params.CharSet,
			BindAddress:        i.Params.Host,
		}}

		i.InsInitDirs[port] = append(i.InsInitDirs[port], []string{insBaseDataDir, insBaseLogDir}...)
	}
	return nil
}
