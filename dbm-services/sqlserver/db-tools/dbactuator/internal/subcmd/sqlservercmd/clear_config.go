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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components/clear"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// ClearConfigAct sqlserver 实例备份数据库
type ClearConfigAct struct {
	*subcmd.BaseOptions
	BaseService clear.ClearConfigComp
}

// ClearConfigCommand godoc
//
// @Summary      sqlserver 清理实例周边配置， 目前支持清理job、linkserver
// @Description  -
// @Tags         sqlserver
// @Accept       json
// @Param        body body      ClearConfigCommand  true  "short description"
func ClearConfigCommand() *cobra.Command {
	act := ClearConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "ClearConfig",
		Short:   "清理实例周边配置",
		Example: fmt.Sprintf(`dbactuator sqlserver ClearConfig %s `, subcmd.CmdBaseExampleStr),
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
func (c *ClearConfigAct) Init() (err error) {
	logger.Info("ClearConfigAct Init")
	if err = c.Deserialize(&c.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return c.BaseService.Init()
}

// Run 执行
func (c *ClearConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "清理配置",
			Func:    c.BaseService.ClearConfig,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("clear config successfully")
	return nil
}
