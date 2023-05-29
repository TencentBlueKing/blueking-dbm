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

// AddDBSInAlwaysOnComp 配置
type AddDBSInAlwaysOnComp struct {
	GeneralParam *components.GeneralParam
	Params       *AddDBSInAlwaysOnParam
	runTimeCtx
}

// AddDBSInAlwaysOnParam 参数
type AddDBSInAlwaysOnParam struct {
	Host      string     `json:"host" validate:"required,ip" `    // 本地hostip
	Port      int        `json:"port"  validate:"required,gt=0"`  // 需要操作的实例端口
	AddSlaves []Instnace `json:"add_slaves"  validate:"required"` // 加入的集群成员
	DBS       []string   `json:"dbs"  validate:"required"`        // 加入到Alwayson组的数据库列表
}

// runTimeCtx 上下文
type runTimeCtx struct {
	DB                *sqlserver.DbWorker
	AlwaysOnGroupName string
	DRS               []AlwaysonInstnce
}

// Init 初始化
func (a *AddDBSInAlwaysOnComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	// 初始化本地实例连接
	if LWork, err = sqlserver.NewDbWorker(
		a.GeneralParam.RuntimeAccountParam.SAUser,
		a.GeneralParam.RuntimeAccountParam.SAPwd,
		a.Params.Host,
		a.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			a.Params.Host, a.Params.Port, err.Error())
		return err
	}
	a.DB = LWork

	// 初始化所有slave实例
	for _, i := range a.Params.AddSlaves {
		var DBWork *sqlserver.DbWorker
		var err error
		if DBWork, err = sqlserver.NewDbWorker(
			a.GeneralParam.RuntimeAccountParam.SAUser,
			a.GeneralParam.RuntimeAccountParam.SAPwd,
			i.Host,
			i.Port,
		); err != nil {
			logger.Error("connenct by [%s:%d] failed,err:%s",
				i.Host, i.Port, err.Error())
			return err
		}

		a.DRS = append(a.DRS, AlwaysonInstnce{
			Host:   i.Host,
			Port:   i.Port,
			Connet: DBWork,
		})
	}
	// 计算alwaysOn 的 group-name
	if a.AlwaysOnGroupName, err = a.DB.GetGroupName(); err != nil {
		return err
	}
	if a.AlwaysOnGroupName == "" {
		return fmt.Errorf(
			"AlwaysOnGroupName is empty in DB[%s:%d]",
			a.Params.Host,
			a.Params.Port,
		)
	}

	return nil
}

// AddDBSInAlwaysOn 把db加入到Alwayson可用组上
func (a *AddDBSInAlwaysOnComp) AddDBSInAlwaysOn() error {
	// 先从主实例执行
	DBSql := fmt.Sprintf(
		cst.ADD_DATABASE_IN_ALWAYS_ON_WITH_DB,
		osutil.ArrayTransString(a.Params.DBS),
	)
	if _, err := a.DB.Exec(DBSql); err != nil {
		logger.Error("exec add dbs in always-on-DB [%s:%d] failed", a.Params.Host, a.Params.Port)
		return err
	}
	// 再从所有实例执行
	for _, s := range a.DRS {
		DRSql := fmt.Sprintf(
			cst.ADD_DATABASE_IN_ALWAYS_ON_WITH_DR,
			osutil.ArrayTransString(a.Params.DBS),
		)
		if _, err := s.Connet.Exec(DRSql); err != nil {
			logger.Error("exec always-on in DR [%s:%d] failed", s.Host, s.Port)
			return err
		}
	}
	return nil
}
