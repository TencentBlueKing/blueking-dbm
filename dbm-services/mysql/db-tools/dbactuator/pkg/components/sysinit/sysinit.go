/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package sysinit TODO
package sysinit

import (
	"fmt"
	"os"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// SysInitParam TODO
type SysInitParam struct {
	OsMysqlUser string `json:"user"`
	OsMysqlPwd  string `json:"pwd"`
}

/*
	执行系统初始化脚本 原来的sysinit.sh
	创建mysql账户等操作
*/

// SysInitMachine TODO
func (s *SysInitParam) SysInitMachine() error {
	logger.Info("start exec sysinit ...")
	return ExecSysInitScript()
}

// SetOsPassWordForMysql TODO
func (s *SysInitParam) SetOsPassWordForMysql() error {
	logger.Info("start set os pwd ...")
	return osutil.SetOSUserPassword(s.OsMysqlUser, s.OsMysqlPwd)
}

// ExecSysInitScript TODO
func ExecSysInitScript() (err error) {
	data, err := staticembed.SysInitMySQLScript.ReadFile(staticembed.SysInitMySQLScriptFileName)
	if err != nil {
		logger.Error("read sysinit script failed %s", err.Error())
		return err
	}
	tmpScriptName := "/tmp/sysinit.sh"
	if err = os.WriteFile(tmpScriptName, data, 07555); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	command := fmt.Sprintf("/bin/bash -c \"%s\"", tmpScriptName)
	_, err = osutil.StandardShellCommand(false, command)
	if err != nil {
		logger.Error("exec sysinit script failed %s", err.Error())
		return err
	}
	return nil
}

// GetTimeZone 增加机器初始化后输出机器的时区配置
func (s *SysInitParam) GetTimeZone() (timeZone string, err error) {
	execCmd := "date +%:z"
	output, err := osutil.StandardShellCommand(false, execCmd)
	if err != nil {
		logger.Error("exec get date script failed %s", err.Error())
		return "", err
	}
	return osutil.CleanExecShellOutput(output), nil

}
