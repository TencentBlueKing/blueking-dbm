/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tbinlogdumpercmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/tbinlogdumper"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DumpSchemaAct TODO
type DumpSchemaAct struct {
	*subcmd.BaseOptions
	Service tbinlogdumper.DumpSchemaComp
}

// NewDumpSchemaCommand godoc
//
// @Summary      备份表结构并导入
// @Description  备份表结构并导入
// @Tags         tbinlogdumper
// @Accept       json
// @Produce      json
// @Param        body body      tbinlogdumper.DumpSchemaComp  true  "short description"
// @Router       /tbinlogdumper/semantic-dumpschema [post]
func NewDumpSchemaCommand() *cobra.Command {
	act := DumpSchemaAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "dumpschema",
		Short: "运行导出并导入表结构",
		Example: fmt.Sprintf(
			`dbactuator tbinlogdumper dumpschema %s %s`,
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
func (d *DumpSchemaAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *DumpSchemaAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *DumpSchemaAct) Run() (err error) {
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
			FunName: "运行导出表结构",
			Func:    d.Service.DumpSchema,
		},
		{
			FunName: "修改表结构的存储引擎",
			Func:    d.Service.ModifyEngine,
		},
		{
			FunName: "导入表结构到TBinlogdumper",
			Func:    d.Service.LoadSchema,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("同步表结构到TBinlogdumper实例成功")
	return nil
}
