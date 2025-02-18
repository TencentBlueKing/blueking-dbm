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

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"

	"github.com/spf13/cobra"
)

// TruncateOnCtlAct TODO
type TruncateOnCtlAct struct {
	*subcmd.BaseOptions
	BaseService truncate.ViaCtlComponent
}

// NewTruncateOnCtlCommand create new subcommand
func NewTruncateOnCtlCommand() *cobra.Command {
	act := TruncateOnCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "truncate-on-ctl"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在中控执行清档",
		Example: fmt.Sprintf(
			`dbactuator spiderctl %s %s %s`,
			subCmdStr,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.BaseService.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (c *TruncateOnCtlAct) Init() error {
	logger.Info("truncate on ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run Command Run
func (c *TruncateOnCtlAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    c.BaseService.Init,
		},
		{
			FunName: "获取清档目标",
			Func:    c.BaseService.GetTarget,
		},
		{
			FunName: "执行清档",
			Func:    c.BaseService.Truncate,
		},
		{
			FunName: "上报删除备份库SQL",
			Func:    c.BaseService.GenerateDropStageSQL,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run truncate on ctl failed, %v", err)
		return err
	}

	logger.Info("truncate on ctl success")
	return nil
}
