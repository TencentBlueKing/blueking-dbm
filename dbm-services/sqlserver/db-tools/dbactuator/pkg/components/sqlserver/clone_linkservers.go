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
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CloneLinkserversComp 克隆用户权限
type CloneLinkserversComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneLinkserversParam
	cloneRunTimeCtx
}

// CloneLinkserversParam 参数
type CloneLinkserversParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	SourceHost string `json:"source_host" validate:"required,ip" `   // 权限源的ip
	SourcePort int    `json:"source_port"  validate:"required,gt=0"` // 权限源的port
}

// LinkserverInfo todo
type LinkserverInfo struct {
	CreateSQL string `db:"linkserver_sql"`
}

// Init 初始化
func (c *CloneLinkserversComp) Init() error {
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

// CloneLinkservers 克隆linkservers
func (c *CloneLinkserversComp) CloneLinkservers() error {
	var getCloneSQLs []LinkserverInfo
	if err := c.SourceDB.Queryx(&getCloneSQLs, cst.GET_LINKSERVERS_INFO); err != nil {
		logger.Error("get linkserver-sql failed")
		return err
	}
	if len(getCloneSQLs) == 0 {
		logger.Warn("[%s:%d] linkserver is not set here, skip", c.Params.SourceHost, c.Params.SourcePort)
		return nil
	}
	// 实例源存在linkserver，则按照指示克隆
	for _, info := range getCloneSQLs {
		// 直接执行sql语句
		if _, err := c.LocalDB.Exec(info.CreateSQL); err != nil {
			logger.Error("exec create linkserver in localDB failed")
			return err
		}

	}
	return nil
}
