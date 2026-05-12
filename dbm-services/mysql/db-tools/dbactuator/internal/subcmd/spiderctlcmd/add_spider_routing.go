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

// AddSpiderRoutingAct 给已有 tendb cluster 添加 spider 节点的路由关系
type AddSpiderRoutingAct struct {
	*subcmd.BaseOptions
	Service spiderctl.AddSpiderRoutingComp
}

// NewAddSpiderRoutingCommand 命令构造
//
// @Summary      给已有tendb cluster集群添加spider节点路由
// @Description  在中控primary节点本机执行, 与 dbm-ui 侧 add_spider_routing.py 等价
// @Tags         spiderctl
// @Accept       json
// @Param        body body      spiderctl.AddSpiderRoutingComp  true  "short description"
// @Router /mysql/add-spider-routing [post]
func NewAddSpiderRoutingCommand() *cobra.Command {
	act := AddSpiderRoutingAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "add-spider-routing",
		Short: "给已有tendb cluster集群添加spider节点路由",
		Example: fmt.Sprintf(
			`dbactuator spiderctl add-spider-routing %s %s`,
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
func (d *AddSpiderRoutingAct) Init() (err error) {
	logger.Info("AddSpiderRoutingAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 执行
func (d *AddSpiderRoutingAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化中控本机连接",
			Func:    d.Service.Init,
		},
		{
			FunName: "前置校验(确认本机为中控primary)",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "添加 spider 路由 + flush routing",
			Func:    d.Service.Run,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("add spider routing successfully")
	return nil
}
