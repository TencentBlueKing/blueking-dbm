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
	"errors"
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// FastExecuteSqlComp dbconsole导出组件
type FastExecuteSqlComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       FastExecuteSqlParam      `json:"extend"`

	executor mysqlutil.ExecuteSqlAtLocal
}

// FastExecuteSqlParam dbconsole 导出参数
type FastExecuteSqlParam struct {
	Socket     string `json:"socket"`
	Host       string `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port       int    `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet    string `json:"charset"`                                     // 字符集参数
	OnDatabase string `json:"database"`

	Force    bool     `json:"force"` // 是否强制执行 执行出错后，是否继续往下执行
	FileDir  string   `json:"file_dir"`
	SqlFiles []string `json:"sql_files"`
}

// Init init,precheck
func (c *FastExecuteSqlComp) Init() (err error) {
	if len(c.Params.SqlFiles) == 0 {
		return errors.New("sql files need given")
	}
	for _, f := range c.Params.SqlFiles {
		sqlFile := filepath.Join(c.Params.FileDir, f)
		if !cmutil.FileExists(sqlFile) {
			err = errors.Join(err, fmt.Errorf("sql file not exists %s", sqlFile))
		}
	}
	taskDir := c.Params.FileDir
	if c.Params.FileDir == "" {
		taskDir = filepath.Dir(c.Params.SqlFiles[0])
	}
	c.executor = mysqlutil.ExecuteSqlAtLocal{
		IsForce:          c.Params.Force,
		Charset:          c.Params.CharSet,
		NeedShowWarnings: false,
		WorkDir:          taskDir,
		User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
		Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
		Host:             c.Params.Host,
		Port:             c.Params.Port,
		Socket:           c.Params.Socket,
	}
	return c.executor.TestConnectionByMySQLClient(c.Params.OnDatabase, true)
}

// Run execute
func (c *FastExecuteSqlComp) Run() (err error) {
	for _, sqlFile := range c.Params.SqlFiles {
		err = c.executor.ExecuteSqlByMySQLClientOne(sqlFile, c.Params.OnDatabase, true)
		if err != nil {
			logger.Error("执行%s文件失败:%s", sqlFile, err.Error())
			if !c.Params.Force {
				return err
			}
		}
	}
	return nil
}

func (c *FastExecuteSqlComp) Example() interface{} {
	return FastExecuteSqlComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			}},
		Params: FastExecuteSqlParam{
			Host:       "x.x.x.x",
			Port:       3306,
			OnDatabase: "test",
			Force:      false,
			FileDir:    "/data/dbbak/",
			SqlFiles:   []string{"aaa.sql", "bbb.priv"},
		},
	}
}
