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
	"encoding/json"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/rollback"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components/sqlserver"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DeploySqlServerAct 部署 sqlserver 实例, 可支持多实例安装
type DeploySqlServerAct struct {
	*subcmd.BaseOptions
	BaseService sqlserver.InstallSqlServerComp
}

// NewDeploySqlServerCommand godoc
//
// @Summary      部署 sqlserver 实例
// @Description  可支持多实例部署
// @Tags         sqlserver
// @Accept       json
// @Param        body body      mysql.InstallSqlServerComp  true  "short description"
func NewDeploySqlServerCommand() *cobra.Command {
	act := DeploySqlServerAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "deploy",
		Short: "部署SqlServer实例",
		Example: fmt.Sprintf(
			`dbactuator sqlserver deploy %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.BaseService.Example()),
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

// Init 初始化
func (d *DeploySqlServerAct) Init() (err error) {
	logger.Info("DeploySpiderAct Init")
	if err = d.Deserialize(&d.BaseService.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.BaseService.GeneralParam = subcmd.GeneralRuntimeParam

	return d.BaseService.InitDefaultParam()
}

// Rollback 回滚
//
//	@receiver d
//	@return err
func (d *DeploySqlServerAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run 执行
func (d *DeploySqlServerAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.BaseService.PreCheck,
		},
		{
			FunName: "生成expoter文件",
			Func:    d.BaseService.CreateExporterConf,
		},
		{
			FunName: "渲染实例配置",
			Func:    d.BaseService.GenerateCnf,
		},
		{
			FunName: "初始化SQLserver相关目录",
			Func:    d.BaseService.InitInstanceDirs,
		},
		{
			FunName: "下载并且解压安装包",
			Func:    d.BaseService.DecompressPkg,
		},
		{
			FunName: "启动SQLserver",
			Func:    d.BaseService.SqlServerStartup,
		},
		{
			FunName: "初始化配置",
			Func:    d.BaseService.InitConfigs,
		},
		{
			FunName: "分配实例BUFFER",
			Func:    d.BaseService.InitInstanceBuffer,
		},
		{
			FunName: "初始化实例",
			Func:    d.BaseService.InitDB,
		},
		{
			FunName: "初始化账号",
			Func:    d.BaseService.InitUsers,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.BaseService.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("install_sqlserver_successfully")
	return nil
}
