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

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// CheckProcesslistExecSQLFileAct TODO
type CheckProcesslistExecSQLFileAct struct {
	*subcmd.BaseOptions
	Payload mysql.ExecuteSQLFileComp
}

const (
	// CheckPlsExecSQLFile check processlist exec sqlfile
	CheckPlsExecSQLFile = "check-pls-exec-sqlfile"
)

// NewCheckProcesslistExecSQLFilCommand TODO
func NewCheckProcesslistExecSQLFilCommand() *cobra.Command {
	act := CheckProcesslistExecSQLFileAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CheckPlsExecSQLFile,
		Short: "SQL导入前检查DDL阻塞",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			CheckPlsExecSQLFile,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate validate
func (d *CheckProcesslistExecSQLFileAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init init
func (d *CheckProcesslistExecSQLFileAct) Init() (err error) {
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run run
func (d *CheckProcesslistExecSQLFileAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    d.Payload.Init,
		},
		{
			FunName: "PreCheck",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "执行DDL阻塞检查",
			Func:    d.Payload.CheckBlockingDDLPcls,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("pre-check blocking ddl process list successfully")
	return nil
}
