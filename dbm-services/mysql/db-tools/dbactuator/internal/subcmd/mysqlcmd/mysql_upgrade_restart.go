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

// UpgradeRestartMySQLAct TODO
type UpgradeRestartMySQLAct struct {
	*subcmd.BaseOptions
	Service upgrade.MysqlUpgradeComp
}

// NewUpgradeRestartMySQLCommand create new subcommand
func NewUpgradeRestartMySQLCommand() *cobra.Command {
	act := UpgradeRestartMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "upgrade-restart",
		Short: "MySQL版本升级重启",
		Example: fmt.Sprintf(
			`dbactuator mysql upgrade-restart %s %s`, subcmd.CmdBaseExampleStr,
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
func (d *UpgradeRestartMySQLAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run Command Run
func (d *UpgradeRestartMySQLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    d.Service.Init,
		},
		{
			FunName: "MySQL重启",
			Func:    d.Service.ReStartMysql,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("mysql upgrade restart successfully")
	return nil
}

// Rollback TODO
func (d *UpgradeRestartMySQLAct) Rollback() (err error) {
	return
}
