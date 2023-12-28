/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package alwayson

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// InitMachineForAlwaysOnComp 配置
type InitMachineForAlwaysOnComp struct {
	GeneralParam *components.GeneralParam
	Params       *InitMachineForAlwaysOnParam
	InitRunTimeCtx
}

// InitMachineForAlwaysOnParam 参数
type InitMachineForAlwaysOnParam struct {
	Host       string     `json:"host" validate:"required,ip" `     // 本地hostip
	Port       int        `json:"port"  validate:"required,gt=0"`   // 需要操作的实例端口
	AddMembers []Instnace `json:"add_members"  validate:"required"` // 集群成员
	IsFirst    bool       `json:"is_first"  validate:"required"`    // 是否第一次部署alwayon
}

type Instnace struct {
	Host string `json:"host" validate:"required,ip" `
	Port int    `json:"port"  validate:"required,gt=0"`
}

type InitRunTimeCtx struct {
	Members []instanceInfo
}

type instanceInfo struct {
	Host         string
	Port         int
	Hostname     string
	InstanceName string
}

// GetinstnaceNameAndHostName 获取实例的hostname 和 instancename
func (i *InitMachineForAlwaysOnComp) GetinstnaceNameAndHostName(host string, port int) error {
	var LWork *sqlserver.DbWorker
	var InsInfo []sqlserver.InstanceInfo
	var err error
	if LWork, err = sqlserver.NewDbWorker(
		i.GeneralParam.RuntimeAccountParam.SAUser,
		i.GeneralParam.RuntimeAccountParam.SAPwd,
		host,
		port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			i.Params.Host, i.Params.Port, err.Error())
		return err
	}
	if InsInfo, err = LWork.GetServerNameAndInstanceName(); err != nil {
		return err
	}
	i.Members = append(i.Members, instanceInfo{
		Host:         host,
		Port:         port,
		Hostname:     InsInfo[0].Hostname,
		InstanceName: InsInfo[0].ServerName,
	})
	return nil
}

// Init 初始化
func (i *InitMachineForAlwaysOnComp) Init() error {
	for _, M := range i.Params.AddMembers {
		if err := i.GetinstnaceNameAndHostName(M.Host, M.Port); err != nil {
			return err
		}
	}
	if i.Params.IsFirst {
		// 如果是第一次部署，则自己信息也要加入一次
		if err := i.GetinstnaceNameAndHostName(i.Params.Host, i.Params.Port); err != nil {
			return err
		}
	}
	return nil
}

// AddItemKey 添加对应的域名解析
func (i *InitMachineForAlwaysOnComp) AddHosts() error {
	for _, inst := range i.Members {
		addHostsExecCmds := []string{
			fmt.Sprintf(
				"Add-Content -Path '%s' -Value '%s %s' ",
				cst.WINDOW_ETC_HOSTS,
				inst.Host,
				inst.Hostname,
			),
		}
		if _, err := osutil.StandardPowerShellCommands(addHostsExecCmds); err != nil {
			return err
		}
	}

	return nil
}

// AddItemKey 添加对应的注册表
func (i *InitMachineForAlwaysOnComp) AddItemKey() error {
	for _, inst := range i.Members {
		addItemExecCmds := []string{
			fmt.Sprintf(
				"New-ItemProperty -Path '%s' -Name %s -PropertyType String -Value 'DBMSSOCN,%s,%d' -Force ",
				cst.WOW6432NODE_CONNECT_TO_KEY,
				inst.InstanceName,
				inst.InstanceName,
				inst.Port,
			),
			fmt.Sprintf(
				"New-ItemProperty -Path '%s' -Name %s -PropertyType String -Value 'DBMSSOCN,%s,%d' -Force ",
				cst.MICROSOFT_CONNECT_TO_KEY,
				inst.InstanceName,
				inst.InstanceName,
				inst.Port,
			),
		}
		if _, err := osutil.StandardPowerShellCommands(addItemExecCmds); err != nil {
			return err
		}
	}
	return nil
}
