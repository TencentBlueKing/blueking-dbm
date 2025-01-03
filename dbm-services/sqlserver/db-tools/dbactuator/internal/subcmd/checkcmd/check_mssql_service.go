/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package checkcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components/check"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// MssqlServiceAct sqlserver 检查实例连接情况
type MssqlServiceAct struct {
	*subcmd.BaseOptions
	BaseService check.MssqlServiceComp
}

// MssqlServiceCommand godoc
//
// @Summary      sqlserver 检查实例连接情况
// @Description  -
// @Tags         sqlserver
// @Accept       json
// @Param        body body      MssqlServiceComp  true  "short description"
func MssqlServiceCommand() *cobra.Command {
	act := MssqlServiceAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "MssqlServiceCheck",
		Short:   "检查机器注册Sqlserver进程情况",
		Example: fmt.Sprintf(`dbactuator check MssqlServiceCheck %s `, subcmd.CmdBaseExampleStr),
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
func (u *MssqlServiceAct) Init() (err error) {
	logger.Info("MssqlServiceAct Init")
	if err = u.Deserialize(&u.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	u.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return nil
}

// Run 执行
func (u *MssqlServiceAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查机器注册Sqlserver进程情况",
			Func:    u.BaseService.CheckMssqlService,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("check-inst-processlists successfully")
	return nil
}
