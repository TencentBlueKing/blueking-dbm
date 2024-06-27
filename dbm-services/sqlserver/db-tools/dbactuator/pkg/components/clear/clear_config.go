/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package clear

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// ClearConfigComp 清理实例周边配置
type ClearConfigComp struct {
	GeneralParam *components.GeneralParam
	Params       *ClearConfigParam
	ClearRunTimeCtx
}

// ClearConfigParam 参数
type ClearConfigParam struct {
	Host              string `json:"host" validate:"required,ip" `   // 本地hostip
	Port              int    `json:"port"  validate:"required,gt=0"` // 需要操作的实例端口
	IsClearJob        bool   `json:"is_clear_job" `                  // 权限源的ip
	IsClearLinkServer bool   `json:"is_clear_linkserver"`            // 权限源的port
}

// 运行是需要的必须参数,可以提前计算
type ClearRunTimeCtx struct {
	LocalDB *sqlserver.DbWorker
}

// Init 初始化
func (c *ClearConfigComp) Init() error {
	var LWork *sqlserver.DbWorker
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
	c.LocalDB = LWork

	return nil
}

// ClearConfig 清理配置
func (c *ClearConfigComp) ClearConfig() error {
	if c.Params.IsClearJob {
		logger.Info("clearing jobs in the instance[%s:%d]", c.Params.Host, c.Params.Port)
		if err := c.ClearJob(); err != nil {
			return fmt.Errorf("clear jobs error:%s", err.Error())
		}
		logger.Info("clear jobs successfully")
	}
	if c.Params.IsClearLinkServer {
		logger.Info("clearing jobs in the instance[%s:%d]", c.Params.Host, c.Params.Port)
		if err := c.ClearLinkServer(); err != nil {
			return fmt.Errorf("clear link-servers error:%s", err.Error())
		}
		logger.Info("clear link-servers successfully")
	}
	return nil
}

// ClearJob 清理实例的job任务
func (c *ClearConfigComp) ClearJob() error {
	if _, err := c.LocalDB.Exec(cst.CLEAR_JOB_SQL); err != nil {
		return err
	}
	return nil
}

// ClearLinkServer 清理实例的linkserver
func (c *ClearConfigComp) ClearLinkServer() error {
	if _, err := c.LocalDB.Exec(cst.CLEAR_LINKSERVER_SQL); err != nil {
		return err
	}
	return nil
}
