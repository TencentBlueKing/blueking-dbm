// Package spiderctlcmd TODO
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

// CheckTdbctlWithSpiderRouterAct check tdbctl with spider schema
type CheckTdbctlWithSpiderRouterAct struct {
	Service spiderctl.CheckTdbctlWithSpideRouterComp
}

// NewChkTdbctlSpiderRouterCommand create new subcommand
func NewChkTdbctlSpiderRouterCommand() *cobra.Command {
	act := CheckTdbctlWithSpiderRouterAct{}
	cmd := &cobra.Command{
		Use:   "check-tdbctl-with-spider-router",
		Short: "检查中控和spider的路由是否一致",
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
func (c *CheckTdbctlWithSpiderRouterAct) Init() (err error) {
	if _, err = subcmd.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run Command Run
func (c *CheckTdbctlWithSpiderRouterAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查集群路由是否和中控一致",
			Func:    c.Service.Run,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("check tdbctl with spider routers successfully")
	return
}
