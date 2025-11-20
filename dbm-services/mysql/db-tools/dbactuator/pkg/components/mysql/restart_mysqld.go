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

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// RestartMysqldComp 需要将 BaseInputParam 转换成 Comp 参数
type RestartMysqldComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       RestartMysqldParam       `json:"extend"`

	// 自动判断的是否 需要重启
	needRestart bool
	ConnMap     map[Port]*native.DbWorker `json:"-"`
	CnfMap      map[Port]*util.CnfFile    `json:"-"`
	socketMap   map[Port]string
	adminUser   string
	adminPwd    string
}

type RestartMysqldParam struct {
	Instances []OneInstance `json:"instances"`
	// ForceShutdown 如果正常关闭实例超时/失败，是否kill来强制关闭实例
	ForceShutdown bool `json:"force_shutdown"`
	// AbortWhenStopped 如果实例已经是 stop 状态，是否放弃 start. 默认 false 意味着继续启动
	AbortWhenInstanceStopped bool `json:"abort_when_instance_stopped"`
	// ContinueOnOtherInstanceError 某个实例重启失败，是否继续操作接下来的实例。默认 false 意味着任务终止
	ContinueOnOtherInstanceError bool `json:"continue_on_other_instance_error"`
}

// Example TODO
func (c *RestartMysqldComp) Example() interface{} {
	comp := RestartMysqldComp{
		Params: RestartMysqldParam{
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
			AbortWhenInstanceStopped:     false,
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

// OneInstance 修改 server_id，会重启
type OneInstance struct {
	Host string `json:"host"`
	Port int    `json:"port"`
}

// Init 用 ADMIN user来重启 mysqld
func (c *RestartMysqldComp) Init() (err error) {
	c.ConnMap = make(map[Port]*native.DbWorker)
	c.socketMap = make(map[Port]string)
	c.CnfMap = make(map[int]*util.CnfFile)
	c.adminUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.adminPwd = c.GeneralParam.RuntimeAccountParam.AdminPwd
	for _, inst := range c.Params.Instances {
		dbConn, err := native.InsObject{
			Host: inst.Host,
			Port: inst.Port,
			User: c.adminUser,
			Pwd:  c.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s...", inst.Port, err.Error())
			if c.Params.AbortWhenInstanceStopped {
				return errors.WithMessagef(err, "abort_when_stopped for %d", inst.Port)
			}
		}

		c.ConnMap[inst.Port] = dbConn
		cnf := &util.CnfFile{FileName: util.GetMyCnfFileName(inst.Port)}
		if err := cnf.Load(); err != nil {
			return err
		}
		socket, err := cnf.GetMySQLSocket()
		if err != nil {
			return err
		}
		c.socketMap[inst.Port] = socket
		c.CnfMap[inst.Port] = cnf
	}
	return nil
}

// PreCheck pre run pre check
func (c *RestartMysqldComp) PreCheck() (err error) {
	// TODO 这里考虑检查 内存配置与 cnf 配置不一样，该怎么处理
	return nil
}

// Start  change my.cnf
func (c *RestartMysqldComp) Start() error {
	var errs error
	for _, inst := range c.Params.Instances {
		if err := computil.RestartMysqlInstanceNormal(native.InsObject{
			Host:   inst.Host,
			Port:   inst.Port,
			User:   c.adminUser,
			Pwd:    c.adminPwd,
			Socket: c.socketMap[inst.Port],
		}); err != nil {
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
