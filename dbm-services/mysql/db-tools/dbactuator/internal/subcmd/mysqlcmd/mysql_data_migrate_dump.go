/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// MysqlDataMigrateDumpAct TODO
type MysqlDataMigrateDumpAct struct {
	*subcmd.BaseOptions
	// 与开区大部分一样，可以服用开区的代码，只在导出库的时候不一样
	Service mysql.OpenAreaDumpSchemaComp
}

// NewMysqlDataMigrateDumpCommand TODO
func NewMysqlDataMigrateDumpCommand() *cobra.Command {
	// *subcmd.BaseOptions是指针变量，需要初始化， subcmd.GBaseOptions在subcmd的init中已被初始化
	act := MysqlDataMigrateDumpAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   "mysql_data_migrate_dump",
		Short: "mysql数据迁移导出库",
		Example: fmt.Sprintf(
			`dbactuator mysql mysql_data_migrate_dump %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate TODO
func (d *MysqlDataMigrateDumpAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *MysqlDataMigrateDumpAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	// d.Deserialize方法执行后，并直接返回值，
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *MysqlDataMigrateDumpAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "precheck",
			Func:    d.Service.Precheck,
		},
		{
			FunName: "运行导出库",
			Func:    d.Service.MysqlDataMigrate,
		},
		{
			FunName: "压缩开区文件",
			Func:    d.Service.CompressDumpDir,
		},
		{
			FunName: "上传库文件",
			Func:    d.Service.Upload,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("mysql数据迁移导出库成功")
	return nil
}
