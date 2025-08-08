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

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/partitionsvr"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

type PartitionExecAct struct {
	*subcmd.BaseOptions
	Service partitionsvr.PartitionExecComp
}

const PartitionExecuteV2 = "partition-execute-v2"

func NewMysqlPartitionExec() *cobra.Command {
	act := PartitionExecAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PartitionExecuteV2,
		Short: "mysql分区执行V2",
		Example: fmt.Sprintf(`dbactuator mysql partition_execute_v2 %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}

	return cmd
}

func (p *PartitionExecAct) Validate() (err error) {
	return p.BaseOptions.Validate()
}

func (p *PartitionExecAct) Init() (err error) {
	if err = p.Deserialize(&p.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	p.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (p *PartitionExecAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    p.Service.Init,
		},
		{
			FunName: "run",
			Func:    p.Service.ExecutePartition,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("分区执行成功")
	return nil
}
