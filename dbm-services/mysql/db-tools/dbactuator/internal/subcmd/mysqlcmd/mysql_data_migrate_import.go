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

// MysqlDataMigrateImportAct TODO
type MysqlDataMigrateImportAct struct {
	*subcmd.BaseOptions
	Service mysql.OpenAreaImportSchemaComp
}

// NewMysqlDataMigrateImportCommand TODO
func NewMysqlDataMigrateImportCommand() *cobra.Command {
	act := MysqlDataMigrateImportAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "mysql_data_migrate_import",
		Short: "mysql数据迁移导入库",
		Example: fmt.Sprintf(
			`dbactuator mysql mysql_data_migrate_import %s %s`,
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
func (d *MysqlDataMigrateImportAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *MysqlDataMigrateImportAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *MysqlDataMigrateImportAct) Run() (err error) {
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
			FunName: "解压schema文件",
			Func:    d.Service.DecompressDumpDir,
		},
		{
			FunName: "创建库",
			Func:    d.Service.CreateDatabase,
		},
		{
			FunName: "导入库文件",
			Func:    d.Service.MysqlDataMigrateImport,
		},
		{
			FunName: "清除dump目录",
			Func:    d.Service.CleanDumpDir,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("开区导入表结构成功")
	return
}
