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

	mssql "github.com/denisenkom/go-mssqldb"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CloneJobsComp 克隆用户权限
type CloneJobsComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneJobsParam
	cloneRunTimeCtx
}

// CloneJobsParam 参数
type CloneJobsParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	SourceHost string `json:"source_host" validate:"required,ip" `   // 权限源的ip
	SourcePort int    `json:"source_port"  validate:"required,gt=0"` // 权限源的port
}

// GetJobsInfos todo
type GetJobsInfos struct {
	JobID      mssql.UniqueIdentifier `db:"job_id"`
	CategoryID int                    `db:"category_id"`
}

// Init 初始化
func (c *CloneJobsComp) Init() error {
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

// CloneJobs 克隆作业
func (c *CloneJobsComp) CloneJobs() error {
	var getJobs []GetJobsInfos
	if err := c.SourceDB.Queryx(&getJobs, cst.GET_JOB_INFOS); err != nil {
		logger.Error("get clone-jobs-info failed")
		return err
	}
	if len(getJobs) == 0 {
		logger.Warn("[%s:%d] jobs is not set here, skip", c.Params.SourceHost, c.Params.SourcePort)
		return nil
	}
	// 存在业务job则同步
	for _, v := range getJobs {
		var getCreateSQL string
		sqlStr := fmt.Sprintf(cst.GET_CREATE_JOB_SQL, v.JobID, v.CategoryID)
		// 拼接create job sql
		if err := c.SourceDB.Queryxs(&getCreateSQL, sqlStr); err != nil {
			logger.Error("get create job in srouceDB failed")
			return err
		}
		// 在本地执行create sql
		if _, err := c.LocalDB.Exec(getCreateSQL); err != nil {
			logger.Error("exec create job in localDB failed")
			return err
		}
	}
	return nil
}
