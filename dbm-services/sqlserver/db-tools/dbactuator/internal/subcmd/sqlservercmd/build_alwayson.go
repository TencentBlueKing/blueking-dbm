/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlservercmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components/sqlserver/alwayson"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// BuildAlwaysOnAct sqlserver 实例之间建立alwayson通信
type BuildAlwaysOnAct struct {
	*subcmd.BaseOptions
	BaseService alwayson.BuildAlwaysOnComp
}

// BuildAlwaysOnCommand godoc
//
// @Summary      sqlserver 实例之间建立alwayson通信
// @Description  -
// @Tags         sqlserver
// @Accept       json
// @Param        body body      BuildAlwaysOnCommand  true  "short description"
func BuildAlwaysOnCommand() *cobra.Command {
	act := BuildAlwaysOnAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "BuildAlwaysOn",
		Short:   "建立alwayson通信",
		Example: fmt.Sprintf(`dbactuator sqlserver BuildAlwaysOn %s `, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化
func (c *BuildAlwaysOnAct) Init() (err error) {
	logger.Info("BuildAlwaysOnAct Init")
	if err = c.Deserialize(&c.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return c.BaseService.Init()
}

// Run 执行
func (c *BuildAlwaysOnAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "建立endpoint",
			Func:    c.BaseService.CreateEndPoint,
		},
		{
			FunName: "建立alwayson通信",
			Func:    c.BaseService.BuildAlwayOn,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("build-always-on successfully")
	return nil
}
