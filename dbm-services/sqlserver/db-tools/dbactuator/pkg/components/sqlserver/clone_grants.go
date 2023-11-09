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
	"encoding/hex"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CloneLoginUsersComp 克隆用户权限
type CloneLoginUsersComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneLoginUsersParam
	cloneRunTimeCtx
}

// CloneLoginUsersParam 参数
type CloneLoginUsersParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	SourceHost string `json:"source_host" validate:"required,ip" `   // 权限源的ip
	SourcePort int    `json:"source_port"  validate:"required,gt=0"` // 权限源的port
}

// 运行是需要的必须参数,可以提前计算
type cloneRunTimeCtx struct {
	LocalDB  *sqlserver.DbWorker
	SourceDB *sqlserver.DbWorker
}

// 定义用户信息的结构
type LoginInfo struct {
	LoginName     string `db:"login_name"`
	Sid           []byte `db:"sid"`
	PasswordHash  []byte `db:"password_hash"`
	DefaultDBName string `db:"default_database_name"`
	SysAdmin      int    `db:"sysadmin"`
	SecurityAdmin int    `db:"securityadmin"`
	ServerAdmin   int    `db:"serveradmin"`
	SetupAdmin    int    `db:"setupadmin"`
	ProcessAdmin  int    `db:"processadmin"`
	DiskAdmin     int    `db:"diskadmin"`
	Dbcreator     int    `db:"dbcreator"`
	BulkAdmin     int    `db:"bulkadmin"`
}

// Init 初始化
func (c *CloneLoginUsersComp) Init() error {
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

// CloneGrant 克隆权限
func (c *CloneLoginUsersComp) CloneGrant() error {
	var logininfos []LoginInfo

	if err := c.SourceDB.Queryx(&logininfos, cst.GET_LOGIN_INFO); err != nil {
		return fmt.Errorf("get-login-info failed %v", err)
	}

	if len(logininfos) == 0 {
		// 表示实例没有非系统用户，正常返回
		logger.Warn("[%s:%d] there is no login user set here", c.Params.SourceHost, c.Params.SourcePort)
		return nil
	}

	// 遍历处理每个login user
	for _, info := range logininfos {
		var execCmds []string
		var isLogin int
		checkCmd := fmt.Sprintf(
			"SELECT count(0) FROM SYS.syslogins WHERE name='%s' and sid = 0x%s;",
			info.LoginName, hex.EncodeToString(info.Sid),
		)
		if err := c.LocalDB.Queryxs(&isLogin, checkCmd); err != nil {
			return err
		}
		if isLogin != 0 {
			// 不等于代表login已在本地实例存在，跳过
			logger.Info("[%s] login user already exists ,skip", info.LoginName)
			continue
		}
		// 本地不存在则克隆
		execCmds = append(execCmds,
			fmt.Sprintf("CREATE LOGIN [%s] WITH PASSWORD=0x%s HASHED,SID=0x%s,DEFAULT_DATABASE=%s,CHECK_POLICY=OFF",
				info.LoginName,
				hex.EncodeToString(info.PasswordHash),
				hex.EncodeToString(info.Sid),
				info.DefaultDBName,
			))
		execCmds = GetLoginCheckRoleName(execCmds, info)

		if _, err := c.LocalDB.ExecMore(execCmds); err != nil {
			logger.Error("clone grants failed %v", err)
			return err
		}

	}
	return nil
}

// GetLoginCheckRoleName todo
// 根据不同admin组的标记，拼接对应的login添加SQL
func GetLoginCheckRoleName(cmds []string, info LoginInfo) []string {
	if info.SysAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'sysadmin'",
			info.LoginName,
		))
	}
	if info.SecurityAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'securityadmin'",
			info.LoginName,
		))
	}
	if info.ServerAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'serveradmin'",
			info.LoginName,
		))
	}
	if info.SetupAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'setupAdmin'",
			info.LoginName,
		))
	}
	if info.ProcessAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'processadmin'",
			info.LoginName,
		))
	}
	if info.DiskAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'diskAdmin'",
			info.LoginName,
		))
	}
	if info.Dbcreator == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'dbcreator'",
			info.LoginName,
		))
	}
	if info.BulkAdmin == 1 {
		cmds = append(cmds, fmt.Sprintf(
			"exec master.dbo.sp_addsrvrolemember @loginame = N'%s', @rolename = N'bulkAdmin'",
			info.LoginName,
		))
	}
	return cmds

}
