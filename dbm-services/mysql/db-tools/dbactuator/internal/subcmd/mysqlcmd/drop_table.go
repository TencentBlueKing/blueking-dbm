// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type DropTableAct struct {
	*subcmd.BaseOptions
	Service mysql.DropTableComp
}

const (
	DropTable = "drop-table"
)

func NewDropTableCommand() *cobra.Command {
	act := DropTableAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   DropTable,
		Short: "删除表",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			DropTable, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *DropTableAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *DropTableAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *DropTableAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "执行前检查",
			Func:    c.Service.PreCheck,
		},
		{
			FunName: "查找数据文件",
			Func:    c.Service.FindDatafiles,
		},
		{
			FunName: "建立硬连接",
			Func:    c.Service.MakeHardlink,
		},
		{
			FunName: "删除表",
			Func:    c.Service.DropTable,
		},
		{
			FunName: "查找遗留硬连接",
			Func:    c.Service.FindLegacyHardlink,
		},
		{
			FunName: "删除硬连接",
			Func:    c.Service.DeleteHardlink,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("删表完成")
	return nil
}
