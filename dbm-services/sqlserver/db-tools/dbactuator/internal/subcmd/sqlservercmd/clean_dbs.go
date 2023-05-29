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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components/sqlserver"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// CleanDBSAct sqlserver DB清档
type CleanDBSAct struct {
	*subcmd.BaseOptions
	BaseService sqlserver.CleanDBSComp
}

// CleanDBSsCommand godoc
//
// @Summary      sqlserver DB清档
// @Description  -
// @Tags         sqlserver
// @Accept       json
// @Param        body body      CleanDBSCommand  true  "short description"
func CleanDBSCommand() *cobra.Command {
	act := CleanDBSAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "CleanDBS",
		Short:   "DB清档",
		Example: fmt.Sprintf(`dbactuator sqlserver CleanDBS %s `, subcmd.CmdBaseExampleStr),
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
func (c *CleanDBSAct) Init() (err error) {
	logger.Info("CleanDBSAct Init")
	if err = c.Deserialize(&c.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return c.BaseService.Init()
}

// Run 执行
func (c *CleanDBSAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检测",
			Func:    c.BaseService.PerCheck,
		},
		{
			FunName: "DB清档",
			Func:    c.BaseService.DoCleanDBS,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("rename-dbs successfully")
	return nil
}
