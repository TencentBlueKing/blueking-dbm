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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// RemoteSlavesComp 配置
type RemoteSlavesComp struct {
	GeneralParam *components.GeneralParam
	Params       *RemoteSlavesParam
	RemoteSlavesRunTimeCtx
}

// RemoteSlavesParam 参数
type RemoteSlavesParam struct {
	Host         string     `json:"host" validate:"required,ip" `        // 本地hostip
	Port         int        `json:"port"  validate:"required,gt=0"`      // 需要操作的实例端口
	RemoteSlaves []Instnace `json:"remotes_slaves"  validate:"required"` // 带移除的集群成员
}

// RemoteSlavesRunTimeCtx todo
type RemoteSlavesRunTimeCtx struct {
	DB                *sqlserver.DbWorker
	AlwaysOnGroupName string
	DRS               []AlwaysonInstnce
}

// Init 初始化
func (b *RemoteSlavesComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	// 初始化本地实例连接
	if LWork, err = sqlserver.NewDbWorker(
		b.GeneralParam.RuntimeAccountParam.SAUser,
		b.GeneralParam.RuntimeAccountParam.SAPwd,
		b.Params.Host,
		b.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			b.Params.Host, b.Params.Port, err.Error())
		return err
	}

	b.DB = LWork
	// 获取可用组名称
	if b.AlwaysOnGroupName, err = b.DB.GetGroupName(); err != nil {
		return err
	}

	// 初始化所有slave实例,如果连接异常则不报错，打印warning日志
	for _, i := range b.Params.RemoteSlaves {
		var DBWork *sqlserver.DbWorker
		var SInfo []sqlserver.InstanceInfo
		var err error
		if DBWork, err = sqlserver.NewDbWorker(
			b.GeneralParam.RuntimeAccountParam.SAUser,
			b.GeneralParam.RuntimeAccountParam.SAPwd,
			i.Host,
			i.Port,
		); err != nil {
			logger.Warn("connenct by [%s:%d] failed,err:%s",
				i.Host, i.Port, err.Error())
			continue
		}
		if SInfo, err = DBWork.GetServerNameAndInstanceName(); err != nil {
			return err
		}

		b.DRS = append(b.DRS, AlwaysonInstnce{
			Host:         i.Host,
			Port:         i.Port,
			Connet:       DBWork,
			InstanceName: SInfo[0].ServerName,
			HostName:     SInfo[0].Hostname,
		})
	}

	return nil
}

// DoRemote 将下架的dr做移除可用组处理
func (b *RemoteSlavesComp) DoRemote() error {
	if err := b.RemoteAlwaysOn(); err != nil {
		return err
	}
	if err := b.RemoteAlwaysOnINDR(); err != nil {
		return err
	}
	return nil
}

// RemoteAlwaysOn 禁用账号
func (b *RemoteSlavesComp) RemoteAlwaysOn() error {
	for _, s := range b.DRS {
		if _, err := b.DB.Exec(
			fmt.Sprintf(cst.REMOTE_ALWAYS_ON_GROUP, s.InstanceName, b.AlwaysOnGroupName, s.InstanceName)); err != nil {
			logger.Error("exec remote group [%s] in DB [%s:%d] failed", s.InstanceName, b.Params.Host, b.Params.Port)
			return err
		}
	}
	return nil
}

// RemoteAlwaysOnINDR 在dr移除可用组信息
func (b *RemoteSlavesComp) RemoteAlwaysOnINDR() error {
	var isError bool = false
	for _, dr := range b.DRS {
		if _, err := dr.Connet.Exec(
			fmt.Sprintf(cst.DELETE_ALWAYS_ON_IN_DR, b.AlwaysOnGroupName, b.AlwaysOnGroupName),
		); err != nil {
			logger.Error("remote always_on in dr [%s:%d]failed %v", dr.Host, dr.Port, err)
			isError = true
		}
	}
	if isError {
		return fmt.Errorf("remote always_on in dr error")

	} else {
		logger.Info("remote always_on in dr successfully")
		return nil
	}

}
