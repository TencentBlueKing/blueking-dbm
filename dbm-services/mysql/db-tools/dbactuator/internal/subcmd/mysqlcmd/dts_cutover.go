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

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dts_cutover"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DtsCutoverAct DTS 安全切换命令
type DtsCutoverAct struct {
	*subcmd.BaseOptions
	Service dts_cutover.Comp
}

const (
	// DtsCutover 命令名
	DtsCutover = "dts-cutover"
)

// NewDtsCutoverCommand godoc
//
// @Summary MySQL DTS 安全切换
// @Description 在 DTS Master 上：预检 → 源表读锁 → 持锁严格复核追平 → Master HTTP API stop → 采位点 → unlock
// @Tags mysql
// @Accept json
// @Param body body dts_cutover.Comp true "description"
// @Router /mysql/dts-cutover [post]
func NewDtsCutoverCommand() *cobra.Command {
	act := DtsCutoverAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   DtsCutover,
		Short: "MySQL DTS 安全切换（预检 + 源表锁 + Master API stop）",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			DtsCutover, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 基本验证
func (c *DtsCutoverAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化
func (c *DtsCutoverAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("dts-cutover params loaded: task=%s deploy_path=%s master=%s",
		c.Service.Params.TaskName, c.Service.Params.DeployPath, c.Service.Params.DtsMasterAddr)
	return nil
}

// Run 执行
func (c *DtsCutoverAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    c.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    c.Service.PreCheck,
		},
		{
			FunName: "DTS 安全切换",
			Func:    c.Service.Run,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("DTS cutover 完成")
	return nil
}
