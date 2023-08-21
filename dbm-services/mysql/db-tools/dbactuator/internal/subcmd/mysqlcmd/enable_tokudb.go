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

	"github.com/spf13/cobra"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
)

// EnableTokudbPluginAct TODO
type EnableTokudbPluginAct struct {
	*subcmd.BaseOptions
	Service mysql.EnableTokudbEngineComp
}

// NewEnableTokudbPluginCommand TODO
func NewEnableTokudbPluginCommand() *cobra.Command {
	act := &EnableTokudbPluginAct{}
	cmd := &cobra.Command{
		Use:   "enable-tokudb-engine",
		Short: "安装tokudb插件",
		Example: fmt.Sprintf(`dbactuator mysql enable-tokudb-engine %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (e *EnableTokudbPluginAct) Init() (err error) {
	if e.BaseOptions, err = subcmd.Deserialize(&e.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	e.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (e *EnableTokudbPluginAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "前置初始化",
			Func:    e.Service.Init,
		},
		{
			FunName: "写入tokudb配置到my.cnf",
			Func:    e.Service.ReWriteMyCnf,
		},
		{
			FunName: "instal tokudb plugin",
			Func:    e.Service.Install,
		},
		{
			FunName: "close db conn",
			Func:    e.Service.CloseConn,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("enable-tokudb-engine success")
	return nil
}
