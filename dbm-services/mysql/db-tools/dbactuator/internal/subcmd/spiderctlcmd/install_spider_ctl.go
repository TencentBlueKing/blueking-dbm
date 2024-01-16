/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctlcmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DeployCtlSpiderAct 部署 spider ctl 实例
type DeployCtlSpiderAct struct {
	*subcmd.BaseOptions
	BaseService mysql.InstallMySQLComp
}

// NewDeploySpiderCtlCommand godoc
//
// @Summary      部署 spider ctl 实例
// @Description  部署 spider ctl 实例说明
// @Tags         spiderctl
// @Accept       json
// @Param        body body      mysql.InstallMySQLComp  true  "short description"
// @Router       /spdierctl/deploy [post]
func NewDeploySpiderCtlCommand() *cobra.Command {
	act := DeployCtlSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "deploy",
		Short: "部署Spider-ctl实例",
		Example: fmt.Sprintf(
			`dbactuator spiderctl deploy %s %s`,
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
func (d *DeployCtlSpiderAct) Init() (err error) {
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
func (d *DeployCtlSpiderAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.Deserialize(&r); err != nil {
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
func (d *DeployCtlSpiderAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.BaseService.PreCheck,
		},
		{
			FunName: "渲染my.cnf配置",
			Func:    d.BaseService.GenerateMycnf,
		},
		{
			FunName: "初始化mysqld相关目录",
			Func:    d.BaseService.InitInstanceDirs,
		},
		{
			FunName: "下载并且解压安装包",
			Func:    d.BaseService.DecompressTdbctlPkg,
		},
		{
			FunName: "初始化mysqld系统库表",
			Func:    d.BaseService.Install,
		},
		{
			FunName: "启动tdbctl",
			Func:    d.BaseService.TdbctlStartup,
		},
		{
			FunName: "执行初始化系统基础权限、库表SQL",
			Func:    d.BaseService.InitDefaultPrivAndSchemaWithResetMaster,
		},
		{
			FunName: "生成exporter配置文件",
			Func:    d.BaseService.CreateExporterCnf,
		},
		{
			FunName: "安装半同步复制插件",
			Func:    d.BaseService.InstallRplSemiSyncPlugin,
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

	logger.Info("install_spider_ctl_successfully")
	return nil
}
