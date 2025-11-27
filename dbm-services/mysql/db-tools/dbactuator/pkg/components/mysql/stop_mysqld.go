// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql

import (
	errors2 "errors"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// StopMysqldComp 需要将 BaseInputParam 转换成 Comp 参数
type StopMysqldComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       StopMysqldParam          `json:"extend"`

	socketMap map[Port]string
	adminUser string
	adminPwd  string
}

type StopMysqldParam struct {
	Instances []OneInstance `json:"instances"`
	// ForceShutdown 如果正常关闭实例超时/失败，是否kill来强制关闭实例
	ForceShutdown bool `json:"force_shutdown"`
	// AlreadyStoppedAsError 如果实例已经是 stop 状态，是否当错误处理。默认 false 表示当做 stop成功
	AlreadyStoppedAsError bool `json:"already_stopped_as_error"`
	// ContinueOnOtherInstanceError 某个实例停止失败，是否继续操作接下来的实例。默认 false 意味着任务终止
	ContinueOnOtherInstanceError bool `json:"continue_on_other_instance_error"`
}

// Example TODO
func (c *StopMysqldComp) Example() interface{} {
	comp := StopMysqldComp{
		Params: StopMysqldParam{
			Instances: []OneInstance{
				{
					Host: "127.0.0.1",
					Port: 20000,
				},
				{
					Host: "127.0.0.1",
					Port: 20001,
				},
			},
			AlreadyStoppedAsError:        false,
			ContinueOnOtherInstanceError: false,
			ForceShutdown:                true,
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// Init 用 ADMIN user来关闭 mysqld
func (c *StopMysqldComp) Init() (err error) {
	c.socketMap = make(map[Port]string)
	c.adminUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.adminPwd = c.GeneralParam.RuntimeAccountParam.AdminPwd
	for _, inst := range c.Params.Instances {
		cnf := &util.CnfFile{FileName: util.GetMyCnfFileName(inst.Port)}
		if err := cnf.Load(); err != nil {
			return err
		}
		socket, err := cnf.GetMySQLSocket()
		if err != nil {
			return err
		}
		c.socketMap[inst.Port] = socket
	}
	return nil
}

// PreCheck pre run pre check
func (c *StopMysqldComp) PreCheck() (err error) {
	// TODO 这里考虑检查 内存配置与 cnf 配置不一样，该怎么处理
	return nil
}

// Start  change my.cnf
func (c *StopMysqldComp) Start() error {
	var errs error
	for _, inst := range c.Params.Instances {
		if isRunning, err := computil.IsInstanceRunning(native.InsObject{
			Host: inst.Host,
			Port: inst.Port,
			User: c.adminUser,
			Pwd:  c.adminPwd,
		}); err == nil && !isRunning && !c.Params.AlreadyStoppedAsError {
			// mysqld 未启动
			continue
		}

		stopInst := computil.ShutdownMySQLParam{
			Host: inst.Host, Port: inst.Port,
			MySQLUser: c.adminUser, MySQLPwd: c.adminPwd,
			Socket: c.socketMap[inst.Port],
		}

		if err := stopInst.ForceShutDownMySQL(); err != nil {
			errs = errors2.Join(errs, err)
			if c.Params.ContinueOnOtherInstanceError {
				continue
			} else {
				return errs
			}
		}
	}
	return errs
}
