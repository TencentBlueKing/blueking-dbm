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

// ClusterBackendSwitchAct TODO
type ClusterBackendSwitchAct struct {
	*subcmd.BaseOptions
	Service spiderctl.SpiderClusterBackendSwitchComp
}

// NewClusterBackendSwitchCommand TODO
func NewClusterBackendSwitchCommand() *cobra.Command {
	act := ClusterBackendSwitchAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "cluster-backend-switch",
		Short: "spider集群后端切换",
		Example: fmt.Sprintf(`dbactuator spiderctl cluster-backend-switch %s %s`,
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

// Init TODO
func (d *ClusterBackendSwitchAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *ClusterBackendSwitchAct) Run() (err error) {
	// 是一个切片
	steps := subcmd.Steps{
		{
			FunName: "[未切换]: 初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "[未切换]: 切换前置检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "[主分片切换中]: 开始切换主分片",
			Func:    d.Service.CutOver,
		},
		{
			FunName: "[主分片切换成功]: 断开NewMaster的同步",
			Func:    d.Service.StopRepl,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("master spt switching has been completed")
	// 如果非强制切换，则需要执行互切的后续操作
	if !d.Service.Params.Force {
		flowSteps := subcmd.Steps{
			{
				FunName: "[主分片切换成功]: 授权repl给OldMaster",
				Func:    d.Service.GrantReplForNewSlave,
			},
			{
				FunName: "[主分片切换成功]: 建立复制关系",
				Func:    d.Service.ChangeMasterToNewMaster,
			},
			{
				FunName: "[开始切换从分片]: 切换从分片",
				Func:    d.Service.SwitchSlaveSpt,
			},
		}
		if err = flowSteps.Run(); err != nil {
			return err
		}
	}
	logger.Info("cluster backend switch successfully")
	return nil
}
