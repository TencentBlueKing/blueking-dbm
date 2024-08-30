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

// CheckTdbctlWithSpiderSchemaAct check tdbctl with spider schema
type CheckTdbctlWithSpiderSchemaAct struct {
	Service spiderctl.CheckTdbctlWithSpideSchemaComp
}

// NewChkTdbctlSpiderSchaCommand create new subcommand
func NewChkTdbctlSpiderSchaCommand() *cobra.Command {
	act := CheckTdbctlWithSpiderSchemaAct{}
	cmd := &cobra.Command{
		Use:   "check-tdbctl-with-spider-schema",
		Short: "spider集群后端切换",
		Example: fmt.Sprintf(`dbactuator spiderctl cluster-backend-switch %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (c *CheckTdbctlWithSpiderSchemaAct) Init() (err error) {
	if _, err = subcmd.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run Command Run
func (c *CheckTdbctlWithSpiderSchemaAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "检查db表数量",
			Func:    c.Service.RunCheck,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("check tdbctl with spider schema successfully")
	return
}
