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

// InitSqlserverInstanceAct sqlserver DB清档
type InitSqlserverInstanceAct struct {
	*subcmd.BaseOptions
	BaseService sqlserver.InitSqlserverInstanceComp
}

// InitSqlserverInstancesCommand godoc
//
// @Summary      sqlserver 实例接入dbm系统初始化
// @Description  -
// @Tags         sqlserver
// @Accept       json
// @Param        body body      InitSqlserverInstanceCommand  true  "short description"
func InitSqlserverInstanceCommand() *cobra.Command {
	act := InitSqlserverInstanceAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "InitSqlserverInstance",
		Short:   "实例接入dbm系统初始化",
		Example: fmt.Sprintf(`dbactuator sqlserver InitSqlserverInstance %s `, subcmd.CmdBaseExampleStr),
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
func (i *InitSqlserverInstanceAct) Init() (err error) {
	logger.Info("InitSqlserverInstanceAct Init")
	if err = i.Deserialize(&i.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	i.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return i.BaseService.Init()
}

// Run 执行
func (i *InitSqlserverInstanceAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "生成exporter配置",
			Func:    i.BaseService.CreateExporterConf,
		},
		{
			FunName: "导出系统库配置",
			Func:    i.BaseService.ExportInstanceConf,
		},
		{
			FunName: "初始化系统库",
			Func:    i.BaseService.InitSysDB,
		},
		{
			FunName: "初始化admin账号",
			Func:    i.BaseService.CreateSysUser,
		},
		{
			FunName: "打印实例的备份配置",
			Func:    i.BaseService.PrintBackupConfig,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("rename-dbs successfully")
	return nil
}
