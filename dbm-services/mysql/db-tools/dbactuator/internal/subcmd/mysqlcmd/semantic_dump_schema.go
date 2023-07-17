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

// SenmanticDumpSchemaAct TODO
type SenmanticDumpSchemaAct struct {
	*subcmd.BaseOptions
	Service mysql.SemanticDumpSchemaComp
}

// NewSenmanticDumpSchemaCommand godoc
//
// @Summary      运行语义检查
// @Description  运行语义检查
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.SemanticDumpSchemaComp  true  "short description"
// @Router       /mysql/semantic-dumpschema [post]
func NewSenmanticDumpSchemaCommand() *cobra.Command {
	act := SenmanticDumpSchemaAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "semantic-dumpschema",
		Short: "运行导出表结构",
		Example: fmt.Sprintf(
			`dbactuator mysql senmantic-check %s %s`,
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
func (d *SenmanticDumpSchemaAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *SenmanticDumpSchemaAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *SenmanticDumpSchemaAct) Run() (err error) {
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
			FunName: "上传表结构",
			Func:    d.Service.Upload,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("导出表结构成功")
	return nil
}
