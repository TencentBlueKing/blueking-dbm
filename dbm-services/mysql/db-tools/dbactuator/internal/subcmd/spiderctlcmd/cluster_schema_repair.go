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

// ClusterSchemaRepairAct TODO
type ClusterSchemaRepairAct struct {
	Service spiderctl.TableSchemaRepairComp
}

// NewClusterSchemaRepairCommand godoc
//
// @Summary      spider 集群表结构修复
// @Description  spider 集群表结构修复
// @Tags         spiderctl
// @Accept       json
// @Param        body body      spiderctl.TableSchemaRepairComp  true  "short description"
// @Router       /spiderctl/schema-repair [post]
func NewClusterSchemaRepairCommand() *cobra.Command {
	act := &ClusterSchemaRepairAct{}
	cmd := &cobra.Command{
		Use:   "schema-repair",
		Short: "spider 集群表结构修复",
		Example: fmt.Sprintf(`dbactuator spiderctl schema-repair %s %s`,
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
func (d *ClusterSchemaRepairAct) Init() (err error) {
	if _, err = subcmd.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *ClusterSchemaRepairAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "集群表结构修复",
			Func: func() error {
				if d.Service.Params.AutoFix {
					logger.Info("根据校验异常的信息去修改集群表结构")
					return d.Service.RunAutoFix()
				}
				return d.Service.Run()
			},
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	return
}
