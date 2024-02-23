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

// BuildAlwaysOnComp 配置
type BuildAlwaysOnComp struct {
	GeneralParam *components.GeneralParam
	Params       *BuildAlwaysOnParam
	CreateRunTimeCtx
}

// BuildAlwaysOnParam 参数
type BuildAlwaysOnParam struct {
	Host      string     `json:"host" validate:"required,ip" `    // 本地hostip
	Port      int        `json:"port"  validate:"required,gt=0"`  // 需要操作的实例端口
	AddSlaves []Instnace `json:"add_slaves"  validate:"required"` // 加入的集群成员
	GroupName string     `json:"group_name"  validate:"required"` // always-on的groupname
	IsFirst   bool       `json:"is_first"  validate:"required"`   // 是否第一次部署alwayon
}

// CreateRunTimeCtx todo
type CreateRunTimeCtx struct {
	DB                *sqlserver.DbWorker
	DBInstanceName    string
	DBHostName        string
	AlwaysOnGroupName string
	DRS               []AlwaysonInstnce
	ListenPort        int
}

// AlwaysonInstnce todo
type AlwaysonInstnce struct {
	Host         string
	Port         int
	InstanceName string
	HostName     string
	Connet       *sqlserver.DbWorker
}

// Init 初始化
func (b *BuildAlwaysOnComp) Init() error {
	var LWork *sqlserver.DbWorker
	var LInfo []sqlserver.InstanceInfo
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
	if LInfo, err = LWork.GetServerNameAndInstanceName(); err != nil {
		return err
	}

	b.DB = LWork
	b.DBHostName = LInfo[0].Hostname
	b.DBInstanceName = LInfo[0].ServerName

	// 初始化所有slave实例
	for _, i := range b.Params.AddSlaves {
		var DBWork *sqlserver.DbWorker
		var SInfo []sqlserver.InstanceInfo
		var err error
		if DBWork, err = sqlserver.NewDbWorker(
			b.GeneralParam.RuntimeAccountParam.SAUser,
			b.GeneralParam.RuntimeAccountParam.SAPwd,
			i.Host,
			i.Port,
		); err != nil {
			logger.Error("connenct by [%s:%d] failed,err:%s",
				i.Host, i.Port, err.Error())
			return err
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
	// 计算endpoint的端口号
	b.ListenPort = osutil.GetListenPort(b.Params.Port)
	// 计算alwaysOn 的 group-name
	if b.Params.IsFirst {
		b.AlwaysOnGroupName = b.Params.GroupName
	} else {
		var name string
		if name, err = b.DB.GetGroupName(); err != nil {
			return err
		}
		b.AlwaysOnGroupName = name
	}
	return nil
}

// CreateEndPoint 建立对端关系
func (b *BuildAlwaysOnComp) CreateEndPoint() error {
	sqlStr := fmt.Sprintf(cst.GET_CREATE_END_POINT_SQL, b.ListenPort, "%s")

	if b.Params.IsFirst {
		// 第一次建立需要在主节点操作
		if _, err := b.DB.Exec(sqlStr); err != nil {
			logger.Error("exec create endpoint in DB [%s:%d] failed", b.Params.Host, b.Params.Port)
			return err
		}
	}
	for _, i := range b.DRS {
		if _, err := i.Connet.Exec(sqlStr); err != nil {
			logger.Error("exec create endpoint in DR [%s:%d] failed", i.Host, i.Port)
			return err
		}
	}
	return nil
}

// BuildAlwayOn 建立AlwayOn
func (b *BuildAlwaysOnComp) BuildAlwayOn() error {
	isAll := "not_all"
	if b.Params.IsFirst {
		isAll = "all"
	}
	for _, s := range b.DRS {
		// 先对主实例添加alwayon实例信息
		DBbuildSQL := fmt.Sprintf(
			cst.CREATE_AlWAYS_ON_IN_DB,
			isAll,
			b.AlwaysOnGroupName,
			b.DBInstanceName,
			b.DBHostName,
			b.ListenPort,
			s.InstanceName,
			b.AlwaysOnGroupName,
			s.InstanceName,
			s.HostName,
			b.ListenPort,
		)
		if _, err := b.DB.Exec(DBbuildSQL); err != nil {
			logger.Error("exec always-on in DB [%s:%d] failed", b.Params.Host, b.Params.Port)
			return err
		}
		// 再在从实例配置Alwayson的信息
		DRbuildSQL := fmt.Sprintf(
			cst.CREATE_AlWAYS_ON_IN_DR,
			b.AlwaysOnGroupName,
		)
		if _, err := s.Connet.Exec(DRbuildSQL); err != nil {
			logger.Error("exec always-on in DR [%s:%d] failed", s.Host, s.Port)
			return err
		}
		// 后面的从实例不需要以创建group信息
		isAll = "not_all"
	}

	return nil
}
