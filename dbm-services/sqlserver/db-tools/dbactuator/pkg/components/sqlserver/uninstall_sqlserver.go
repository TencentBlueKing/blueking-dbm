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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// UnInstallSQLServerComp 卸载SQLServer
type UnInstallSQLServerComp struct {
	GeneralParam *components.GeneralParam
	Params       *UnInstallSQLServerParam
	runTimeCtx
}

// UnInstallSQLServerParam 参数
type UnInstallSQLServerParam struct {
	Host  string `json:"host" validate:"required,ip" `
	Force bool   `json:"force"`                                // 是否强制下架
	Ports []int  `json:"ports"  validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口

}

// 运行是需要的必须参数,可以提前计算
type runTimeCtx struct {
	insObj map[Port]*obj
}

// obj 每个实例当前状态
type obj struct {
	InstanceName string
	IsShutdown   bool // 标记卸载的实例是否已经是关闭/不能访问的状态
}

// Init 初始化
func (u *UnInstallSQLServerComp) Init() error {
	u.insObj = make(map[int]*obj)
	for _, port := range u.Params.Ports {
		u.insObj[port] = &obj{
			InstanceName: "",
			IsShutdown:   false, // 初始化给个默认值，后续判断实例是否正常才变更
		}
	}
	return nil

}

// PreCheck 预检查
// 检查实例连接
func (u *UnInstallSQLServerComp) PreCheck() error {
	var isPass bool = true
	checkCmd := "SELECT count(0) FROM SYS.SYSPROCESSES WHERE LOGINAME NOT LIKE '%\\%' " +
		"AND LOGINAME NOT LIKE '%#%' AND  LOGINAME NOT LIKE  'distributor%' AND  LOGINAME not in('sa','monitor')"
	for _, port := range u.Params.Ports {
		var dbWork *sqlserver.DbWorker
		var err error
		var cnt int
		if dbWork, err = sqlserver.NewDbWorker(
			u.GeneralParam.RuntimeAccountParam.SAUser,
			u.GeneralParam.RuntimeAccountParam.SAPwd,
			u.Params.Host,
			port,
		); err != nil {
			logger.Warn("connenct by %d failed,err:%s", port, err.Error())
			logger.Warn("this port [%d] is considered closed", port)
			// 连接不上标记为实例已关闭状态
			u.insObj[port].IsShutdown = true
			continue
		}
		// 到最后回收db连接
		defer dbWork.Stop()

		if err := dbWork.Queryxs(&cnt, checkCmd); err != nil {
			logger.Error("check processlist failed %v", err)
			isPass = false
		}
		if cnt != 0 && !u.Params.Force {
			// 存在用户连接且安全下架情况，退出异常
			logger.Error("There is a business connections [%d] on this port [%d]", cnt, port)
			isPass = false

		} else {
			// 检测通过，获取实例名称
			if err := dbWork.Queryxs(
				&u.insObj[port].InstanceName,
				"SELECT SERVERPROPERTY('InstanceName') ;"); err != nil {
				return fmt.Errorf("[%d] check InstanceName failed %v", port, err)
			}
		}
	}
	if !isPass {
		return fmt.Errorf("prechek failed")
	}
	return nil
}

// ShutDownMSSQL TODO
// PreCheck 关闭MSSQL进程
func (u *UnInstallSQLServerComp) ShutDownMSSQL() error {
	// 按照实例关闭进程
	for _, port := range u.Params.Ports {
		if u.insObj[port].IsShutdown {
			logger.Info(" The port [%d]  skips closing ", port)
			continue
		}
		cmds := []string{
			fmt.Sprintf("Stop-Service -Name \"SQLAGENT`$%s\"", u.insObj[port].InstanceName),
			fmt.Sprintf("Stop-Service -Name \"MSSQL`$%s\"", u.insObj[port].InstanceName),
			fmt.Sprintf("Set-Service -Name \"SQLAGENT`$%s\" -StartupType Disabled ", u.insObj[port].InstanceName),
			fmt.Sprintf("Set-Service -Name \"MSSQL`$%s\" -StartupType Disabled ", u.insObj[port].InstanceName),
		}
		if _, err := osutil.StandardPowerShellCommands(cmds); err != nil {
			return err
		}
	}
	return nil
}
