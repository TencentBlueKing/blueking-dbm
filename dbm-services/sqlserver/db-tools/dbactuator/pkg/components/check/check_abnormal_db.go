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

// CheckAbnormalDBComp 检查异常db信息
type CheckAbnormalDBComp struct {
	GeneralParam *components.GeneralParam
	Params       *CheckAbnormalDBParam
	DB           *sqlserver.DbWorker
}

// CheckAbnormalDBParam 参数
type CheckAbnormalDBParam struct {
	Host string `json:"host" validate:"required,ip" `   // 本地hostip
	Port int    `json:"port"  validate:"required,gt=0"` // 需要操作的实例端口
}

// Init 初始化
func (c *CheckAbnormalDBComp) Init() error {
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

// CheckAbnormalDB 检查异常db
func (c *CheckAbnormalDBComp) CheckAbnormalDB() error {
	var adnormalDBS []string
	checkCmd := "select name from master.sys.databases where is_read_only <> 0 or state <> 0;"
	if err := c.DB.Queryx(&adnormalDBS, checkCmd); err != nil {
		return fmt.Errorf("check-abnormal-db failed %v", err)
	}
	if len(adnormalDBS) == 0 {
		// 没有返回异常db列表则正常退出
		return nil
	}
	// 异常退出
	return fmt.Errorf(
		"[%s:%d] there is an exception or a read-only databases [%v], please check",
		c.Params.Host,
		c.Params.Port,
		adnormalDBS,
	)

}
