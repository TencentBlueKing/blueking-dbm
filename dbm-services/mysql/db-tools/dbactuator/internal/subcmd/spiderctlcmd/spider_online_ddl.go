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

// SpiderOnlineDDLAct use online ddl tools to change schema
type SpiderOnlineDDLAct struct {
	*subcmd.BaseOptions
	Service spiderctl.SpiderOnlineDDLComp
}

// NewSpiderOnlineDDLCommand create new subcommand
func NewSpiderOnlineDDLCommand() *cobra.Command {
	act := SpiderOnlineDDLAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "do-online-ddl",
		Short: "使用gh-ost工具执行online ddl",
		Example: fmt.Sprintf(
			`dbactuator spiderctl do-online-ddl %s %s`,
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
func (d *SpiderOnlineDDLAct) Init() (err error) {
	logger.Info("SpiderOnlineDDLAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run Command Run
func (d *SpiderOnlineDDLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "precheck",
			Func:    d.Service.Precheck,
		},
		{
			FunName: "执行online ddl",
			Func:    d.Service.Execute,
		},
		{
			FunName: "clean env",
			Func:    d.Service.Close,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("do online ddl successfully")
	return err
}
