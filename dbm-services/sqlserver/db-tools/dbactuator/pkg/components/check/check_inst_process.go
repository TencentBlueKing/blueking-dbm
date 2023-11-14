/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package check

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CheckInstProcessComp 检查db连接情况
type CheckInstProcessComp struct {
	GeneralParam *components.GeneralParam
	Params       *CheckAbnormalDBParam
	DB           *sqlserver.DbWorker
}

// CheckInstProcessParam 参数
type CheckInstProcessParam struct {
	Host string `json:"host" validate:"required,ip" `   // 本地hostip
	Port int    `json:"port"  validate:"required,gt=0"` // 需要操作的实例端口
}

// 定义连接状态的结构
type ProcessInfo struct {
	Spid        int    `db:"spid"`
	DbName      string `db:"dbname"`
	Cmd         string `db:"cmd"`
	Status      string `db:"status"`
	ProgramName string `db:"program_name"`
	Hostname    string `db:"hostname"`
	LoginTime   string `db:"login_time"`
}

// Init 初始化
func (c *CheckInstProcessComp) Init() error {
	var dbWork *sqlserver.DbWorker
	var err error
	if dbWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		// 如果实例连接失败，则退出异常
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.DB = dbWork

	return nil

}

// CheckInstProcess 检查db连接情况
func (c *CheckInstProcessComp) CheckInstProcess() error {
	var procinfos []ProcessInfo
	checkCmd := "select spid, DB_NAME(dbid) as dbname ,cmd, status, program_name,hostname, login_time" +
		" from master.sys.sysprocesses where dbid >4  and dbid != DB_ID('Monitor') order by login_time desc;"
	if err := c.DB.Queryx(&procinfos, checkCmd); err != nil {
		return fmt.Errorf("check-abnormal-db failed %v", err)
	}
	if len(procinfos) == 0 {
		// 没有返回异常db列表则正常退出
		return nil
	}
	// 异常退出
	for _, info := range procinfos {
		logger.Error("process:[%+v]", info)
	}
	return fmt.Errorf(
		"[%s:%d] there is a business connections [%d], please check",
		c.Params.Host,
		c.Params.Port,
		len(procinfos),
	)

}
