/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctlcmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spiderctl"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// ImportSchemaFromLocalSpiderAct 从本地Spider导入表结构到中控节点
type ImportSchemaFromLocalSpiderAct struct {
	*subcmd.BaseOptions
	Service spiderctl.ImportSchemaFromLocalSpiderComp
}

// NewImportSchemaToTdbctlCommand create new subcommand
func NewImportSchemaToTdbctlCommand() *cobra.Command {
	act := ImportSchemaFromLocalSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "import-schema-to-tdbctl",
		Short: "从spider节点导入表结构到中控节点",
		Example: fmt.Sprintf(
			`dbactuator spiderctl import-schema-to-tdbctl %s %s`,
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

// Init 初始化
func (d *ImportSchemaFromLocalSpiderAct) Init() (err error) {
	logger.Info("InitCLusterRoutingAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 执行
func (d *ImportSchemaFromLocalSpiderAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "从本地spider导出表结构至tdbctl",
			Func:    d.Service.Migrate,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("import schema to empty tdbctl succcess ~")
	return nil
}
