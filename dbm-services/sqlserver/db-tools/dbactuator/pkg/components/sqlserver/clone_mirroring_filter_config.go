/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

const MIRRORING_FILTER_TABLE = "[Monitor].[dbo].[MIRRORING_FILTER]"

// CloneMirroringFilterComp 克隆用户权限
type CloneMirroringFilterComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneMirroringFilterParam
	cloneMirroringRunTimeCtx
}

// CloneMirroringFilterParam 参数
type CloneMirroringFilterParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	SourceHost string `json:"source_host" validate:"required,ip" `   // 权限源的ip
	SourcePort int    `json:"source_port"  validate:"required,gt=0"` // 权限源的port
}

// 运行是需要的必须参数,可以提前计算
type cloneMirroringRunTimeCtx struct {
	LocalDB  *sqlserver.DbWorker
	SourceDB *sqlserver.DbWorker
}

type MirroringFilterInfo struct {
	Name string `db:"NAME"`
}

// Init 初始化
func (c *CloneMirroringFilterComp) Init() error {
	var LWork *sqlserver.DbWorker
	var SWork *sqlserver.DbWorker
	var err error
	if LWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	if SWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.SourceHost,
		c.Params.SourcePort,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.SourceHost, c.Params.SourcePort, err.Error())
		return err
	}
	c.LocalDB = LWork
	c.SourceDB = SWork

	return nil
}

// CopyMirroringFilterTable 克隆Mirroring_filter表数据
// 步骤：
// 1: 删除目标实例的Mirroring_filter表
// 2:拉取原实例的Mirroring_filter表， 同时插入到目标实例
func (c *CloneMirroringFilterComp) CopyMirroringFilterTable() error {
	var MirroringFilters []MirroringFilterInfo
	var insertSqls []string
	truncateSql := fmt.Sprintf("truncate table %s", MIRRORING_FILTER_TABLE)
	getSql := fmt.Sprintf("select * from %s", MIRRORING_FILTER_TABLE)

	// 1: 删除目标实例的Mirroring-filter表
	if _, err := c.LocalDB.Exec(truncateSql); err != nil {
		logger.Error("truncate table %s failed %v", MIRRORING_FILTER_TABLE, err)
		return err
	}

	// 2:拉取原实例的Mirroring-filter表
	if err := c.SourceDB.Queryx(&MirroringFilters, getSql); err != nil {
		return fmt.Errorf("select %s failed %v", MIRRORING_FILTER_TABLE, err)
	}

	// 同时插入到目标实例
	for _, info := range MirroringFilters {
		insertSqls = append(
			insertSqls,
			fmt.Sprintf("insert into %s values('%s')",
				MIRRORING_FILTER_TABLE, info.Name),
		)
	}
	if len(insertSqls) == 0 {
		logger.Warn("copy-Mirroring-filter-record is null")
		return nil
	}
	if _, err := c.LocalDB.ExecMore(insertSqls); err != nil {
		logger.Error("insert table %s failed %v", MIRRORING_FILTER_TABLE, err)
		return err
	}
	return nil
}
