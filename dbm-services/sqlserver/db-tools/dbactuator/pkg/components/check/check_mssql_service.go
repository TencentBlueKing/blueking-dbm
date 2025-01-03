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
	"bk-dbconfig/pkg/core/logger"
	"fmt"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// MssqlServiceComp 检查db连接情况
type MssqlServiceComp struct {
	GeneralParam *components.GeneralParam
	Params       *MssqlServiceParam
	DB           *sqlserver.DbWorker
}

// MssqlServiceParam 参数
type MssqlServiceParam struct {
	Host string `json:"host" validate:"ip" ` // 本地hostip
}

// CheckMssqlService 检查机器注册Sqlserver进程情况
func (c *MssqlServiceComp) CheckMssqlService() error {
	var checkresult string
	ret, err := osutil.StandardPowerShellCommand(
		"GET-SERVICE -NAME MSSQL* | WHERE-OBJECT {$_.NAME -NOTLIKE \"*#*\"}",
	)
	if err != nil {
		return err
	}
	if ret != "" {
		// 输出不为空则表示有部署进程
		logger.Info("there is a mssql process has been registered [%s]", osutil.CleanExecOutput(ret))
		checkresult = "1"
	}
	logger.Info("no mssql service registered")
	checkresult = "0"
	components.WrapperOutputString(fmt.Sprintf("{\"checkresult\": \"%s\"}", checkresult))
	return nil

}
