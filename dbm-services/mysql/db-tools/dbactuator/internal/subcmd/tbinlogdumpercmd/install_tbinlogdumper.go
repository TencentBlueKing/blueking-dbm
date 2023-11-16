/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tbinlogdumpercmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/tbinlogdumper"
	"dbm-services/mysql/db-tools/dbactuator/pkg/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DeployTbinlogDumperAct TODO
type DeployTbinlogDumperAct struct {
	*subcmd.BaseOptions
	Service tbinlogdumper.InstallTbinlogDumperComp
}

// NewDeployTbinlogDumperCommand godoc
//
// @Summary      部署 tbinlogdumper 实例
// @Description  部署 tbinlogdumper 实例说明
// @Tags         tbinlogdumper
// @Accept       json
// @Param        body body      tbinlogdumper.InstallTbinlogDumperComp  true  "short description"
// @Router       /tbinlogdumper/deploy [post]
func NewDeployTbinlogDumperCommand() *cobra.Command {
	act := DeployTbinlogDumperAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "deploy",
		Short: "部署TbinlogDumper实例",
		Example: fmt.Sprintf(
			`dbactuator tbinlogdumper deploy %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
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

// Init TODO
func (d *DeployTbinlogDumperAct) Init() (err error) {
	logger.Info("DeployMySQLAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	// 解析额外参数
	if err = d.Deserialize(&d.Service.Configs); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDumperDefaultParam()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *DeployTbinlogDumperAct) Rollback() (err error) {
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

// Run TODO
func (d *DeployTbinlogDumperAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "渲染tbinlogdumper配置",
			Func:    d.Service.GenerateDumperMycnf,
		},
		{
			FunName: "初始化tbinlogdumper相关目录",
			Func:    d.Service.InitInstanceDirs,
		},
		{
			FunName: "下载并且解压安装包",
			Func:    d.Service.DecompressDumperPkg,
		},
		{
			FunName: "初始化系统库表",
			Func:    d.Service.DumperInstall,
		},
		{
			FunName: "启动tbinlogdumper",
			Func:    d.Service.Startup,
		},
		{
			FunName: "执行初始化系统基础权限、库表SQL",
			Func:    d.Service.InitDefaultPrivAndSchemaWithResetMaster,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("install_tbinlogdumper successfully")
	return nil
}
