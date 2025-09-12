// Package mysqlcmd TODO
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
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/upgrade"
)

// UpgradeStartMySQLAct TODO
type UpgradeStartMySQLAct struct {
	*subcmd.BaseOptions
	Service upgrade.MysqlUpgradeComp
}

// NewUpgradeStartMySQLCommand create new subcommand
func NewUpgradeStartMySQLCommand() *cobra.Command {
	act := UpgradeStartMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "upgrade-start",
		Short: "MySQL版本升级启动",
		Example: fmt.Sprintf(
			`dbactuator mysql upgrade-start %s %s`, subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Params),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (d *UpgradeStartMySQLAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run Command Run
func (d *UpgradeStartMySQLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    d.Service.StartInit,
		},
		{
			FunName: "MySQL启动",
			Func:    d.Service.StartMysql,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("mysql upgrade start successfully")
	return nil
}

// Rollback TODO
func (d *UpgradeStartMySQLAct) Rollback() (err error) {
	return
}
