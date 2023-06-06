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

// ClusterBackendMigrateCutOverAct TODO
type ClusterBackendMigrateCutOverAct struct {
	*subcmd.BaseOptions
	Service spiderctl.SpiderClusterBackendMigrateCutoverComp
}

// NewClusterMigrateCutOverCommand TODO
func NewClusterMigrateCutOverCommand() *cobra.Command {
	act := ClusterBackendMigrateCutOverAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "cluster-backend-migrate-cutover",
		Short: "spider集群后端迁移切换",
		Example: fmt.Sprintf(`dbactuator spiderctl cluster-backend-migrate-cutover %s %s`,
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
func (d *ClusterBackendMigrateCutOverAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *ClusterBackendMigrateCutOverAct) Run() (err error) {
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
			FunName: "[主分片切换中]: 开始切换",
			Func:    d.Service.CutOver,
		},
		{
			FunName: "[已完成切换]: 断开数据同步",
			Func:    d.Service.StopRepl,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("cluster backend migrate cutover successfully")
	return nil
}
