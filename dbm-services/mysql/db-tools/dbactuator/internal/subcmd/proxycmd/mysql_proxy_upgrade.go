// Package proxycmd TODO
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package proxycmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// MySQLProxyUpgradeAct TODO
type MySQLProxyUpgradeAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.UpgradeProxyComp
}

// NewMySQLProxyUpgradeAct TODO
func NewMySQLProxyUpgradeAct() *cobra.Command {
	act := MySQLProxyUpgradeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "upgrade",
		Short: "升级mysql-proxy实例",
		Example: fmt.Sprintf("dbactuator proxy upgrade %s %s", subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (c *MySQLProxyUpgradeAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run Command Run
func (c *MySQLProxyUpgradeAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "前置检查",
			Func:    c.Service.PreCheck,
		},
		{
			FunName: "升级替换介质包",
			Func:    c.Service.ReplaceMedium,
		},
		{
			FunName: "重启proxy",
			Func:    c.Service.RestartProxy,
		},
		{
			FunName: "refresh backend",
			Func:    c.Service.RefreshBackends,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("完成本地升级: 成功")
	return nil
}
