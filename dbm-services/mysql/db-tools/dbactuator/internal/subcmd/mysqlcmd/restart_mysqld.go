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

// RestartMysqldAct TODO
type RestartMysqldAct struct {
	*subcmd.BaseOptions
	Payload mysql.RestartMysqldComp
}

// RestartMysqldCommand godoc
//
// @Summary      重启 mysqld
// @Description  重启 mysqld
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.RestartMysqldComp  true  "description"
// @Router       /mysql/restart-mysqld[post]
func RestartMysqldCommand() *cobra.Command {
	act := RestartMysqldAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "restart-mysqld",
		Short: "修改mysql配置",
		Example: fmt.Sprintf(
			`dbactuator mysql restart-mysqld %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
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
func (d *RestartMysqldAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	logger.Warn("params %+v", d.Payload.Params)
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (d *RestartMysqldAct) Validate() error {
	return nil
}

// Run TODO
func (d *RestartMysqldAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "加载配置文件",
			Func:    d.Payload.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "重启 mysqld",
			Func:    d.Payload.Start,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("restart mysqld successfully")
	return nil
}
