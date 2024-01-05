/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spidercmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spider"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// UpgradeSpiderAct TODO
type UpgradeSpiderAct struct {
	*subcmd.BaseOptions
	Service spider.UpgradeSpiderComp
}

// NewUpgradeSpiderCommand create new subcommand
func NewUpgradeSpiderCommand() *cobra.Command {
	act := UpgradeSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "upgrade",
		Short: "本地升級spider",
		Example: fmt.Sprintf(`dbactuator spider upgrade %s %s`,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (d *UpgradeSpiderAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run Command Run
func (d *UpgradeSpiderAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "替换介质版本",
			Func:    d.Service.ReplaceMedium,
		},
		{
			FunName: "初始化spider系统表",
			Func:    d.Service.CreateSpiderTable,
		},
		{
			FunName: "重启spider",
			Func:    d.Service.Restart,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("upgrade local spider successfully")
	return nil
}
