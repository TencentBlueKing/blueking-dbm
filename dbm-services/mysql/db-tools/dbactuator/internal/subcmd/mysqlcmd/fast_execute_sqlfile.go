// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

type FastExecuteSqlAct struct {
	*subcmd.BaseOptions
	Service mysql.FastExecuteSqlComp
}

const SubCmdFastExecuteSqlFile = "fast-execute-sql-file"

// NewFastExecuteSqlActCommand godoc
//
// @Summary  快速执行 sql 文件
// @Description  通过 mysql 客户端导入 sql
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.FastExecuteSqlComp  true  "short description"
// @Router       /mysql/fast-execute-sql-file [post]
func NewFastExecuteSqlActCommand() *cobra.Command {
	act := FastExecuteSqlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   SubCmdFastExecuteSqlFile,
		Short: "快速执行 sql 文件",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			SubCmdFastExecuteSqlFile, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *FastExecuteSqlAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *FastExecuteSqlAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *FastExecuteSqlAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "执行",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("sql 文件导入完成")
	return nil
}
