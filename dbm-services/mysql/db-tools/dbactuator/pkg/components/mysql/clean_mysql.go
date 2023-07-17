/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"

	"github.com/pkg/errors"
)

// CleanMysqlComp 需要将 BaseInputParam 转换成 Comp 参数
type CleanMysqlComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       CleanMysqlParam          `json:"extend"`
	ctx
}

// Example TODO
func (c *CleanMysqlComp) Example() interface{} {
	comp := CleanMysqlComp{
		Params: CleanMysqlParam{
			StopSlave:   true,
			ResetSlave:  true,
			Force:       false,
			TgtInstance: &common.InstanceExample,
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// CleanMysqlParam 删除目标实例里面的所有 database
// 保留系统库，如 mysql,infodba_schema, sys 等
type CleanMysqlParam struct {
	// 是否执行 stop slave
	StopSlave bool `json:"stop_slave"`
	// 是否执行 reset slave all
	ResetSlave bool `json:"reset_slave"`
	// drop_database 之后是否重启实例
	Restart bool `json:"restart"`
	// 当实例不空闲时是否强制清空
	Force bool `json:"force"`
	// 是否执行 drop database，这里是确认行为. 如果 false 则只把 drop 命令打印到输出
	DropDatabase     bool `json:"drop_database"`
	CheckIntervalSec int  `json:"check_interval_sec"`
	// 清空目标实例
	TgtInstance *native.Instance `json:"tgt_instance" validate:"required"`
}

type ctx struct {
	sysUsers      []string
	checkDuration time.Duration
	myCnf         *util.CnfFile
	dbworker      *native.DbWorker
	instObj       *native.InsObject
}

// Init TODO
func (c *CleanMysqlComp) Init() error {
	f := util.GetMyCnfFileName(c.Params.TgtInstance.Port)
	c.myCnf = &util.CnfFile{FileName: f}
	if err := c.myCnf.Load(); err != nil {
		return err
	}
	dbSocket, err := c.myCnf.GetMySQLSocket()
	if err != nil {
		return err
	}
	c.instObj = &native.InsObject{
		Host:   c.Params.TgtInstance.Host,
		Port:   c.Params.TgtInstance.Port,
		User:   c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:    c.GeneralParam.RuntimeAccountParam.AdminPwd,
		Socket: dbSocket,
	}
	if dbw, err := c.instObj.ConnBySocket(); err != nil {
		return err
	} else {
		c.dbworker = dbw
	}
	if c.Params.CheckIntervalSec == 0 {
		c.Params.CheckIntervalSec = 31
	}
	c.checkDuration = time.Duration(c.Params.CheckIntervalSec) * time.Second
	return nil
}

// PreCheck 前置检查
// 会初始化 needRestart
func (c *CleanMysqlComp) PreCheck() error {
	if err := c.instObj.CheckInstanceConnIdle(c.GeneralParam.GetAllSysAccount(),
		c.checkDuration); err != nil {
		logger.Warn("clean_mysql precheck error %w", err)
		if c.Params.Force {
			return nil
		}
		return err
	}
	return nil
}

// Start TODO
func (c *CleanMysqlComp) Start() error {
	if c.Params.StopSlave {
		if err := c.dbworker.StopSlave(); err != nil {
			return errors.WithMessage(err, "stop slave")
		}
	}
	if c.Params.ResetSlave {
		if err := c.dbworker.ResetSlave(); err != nil {
			return errors.WithMessage(err, "reset slave")
		}
	}

	// 计划删除的 databases 列表
	inStr, _ := mysqlutil.UnsafeBuilderStringIn(native.DBSys, "'")
	dbsSql := fmt.Sprintf("select SCHEMA_NAME from information_schema.SCHEMATA where SCHEMA_NAME not in (%s)", inStr)

	if databases, err := c.dbworker.Query(dbsSql); err != nil {
		if c.dbworker.IsNotRowFound(err) {
			return nil
		} else {
			return err
		}
	} else {
		for _, dbName := range databases {
			dropSQL := fmt.Sprintf("DROP DATABASE `%s`;", dbName["SCHEMA_NAME"])
			logger.Warn("run sql %s", dropSQL)
			if c.Params.DropDatabase {
				if _, err := c.dbworker.Exec(dropSQL); err != nil {
					return errors.WithMessage(err, dropSQL)
				}
			} else {
				fmt.Printf("%s -- not run because drop_database=false\n", dropSQL)
			}
		}
		if c.Params.DropDatabase && c.Params.Restart {
			if err := computil.RestartMysqlInstanceNormal(*c.instObj); err != nil {
				return err
			}
		}
	}
	return nil
}
