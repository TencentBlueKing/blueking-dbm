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

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spiderctl"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// AddSlaveClusterRoutingAct TODO
//
//	AddSlaveClusterRoutingAct  添加spider slave集群时，添加相关路由信息
type AddSlaveClusterRoutingAct struct {
	Service spiderctl.AddSlaveClusterRoutingComp
}

// AddSlaveClusterRoutingCommand TODO
func AddSlaveClusterRoutingCommand() *cobra.Command {
	act := AddSlaveClusterRoutingAct{}
	cmd := &cobra.Command{
		Use:   "add-slave-cluster-routing",
		Short: "添加spider-slave集群的相关路由信息",
		Example: fmt.Sprintf(`dbactuator spiderctl add-slave-cluster-routing %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化
func (d *AddSlaveClusterRoutingAct) Init() (err error) {
	logger.Info("InitCLusterRoutingAct Init")
	if _, err = subcmd.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 执行
func (d *AddSlaveClusterRoutingAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "执行前检验",
			Func:    d.Service.PerCheck,
		},

		{
			FunName: "添加slave集群路由信息",
			Func:    d.Service.AddSlaveRouting,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("add slave clsuter routing relationship successfully")
	return nil
}
