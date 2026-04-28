/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package oscmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/oscomp"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// DiskBenchmarkAct disk-benchmark 子命令 Act
type DiskBenchmarkAct struct {
	*subcmd.BaseOptions
	Payload oscomp.DiskBenchmarkComp
}

// NewDiskBenchmarkCommand register disk-benchmark sub command
//
// @Summary      磁盘性能压测 (文件模式 only)
// @Description  在指定文件路径上跑 5 阶段 fio 类压测，输出 BaselineDisk 兼容字段
// @Tags         os
// @Accept       json
// @Param        body body      oscomp.DiskBenchmarkParams  true  "payload extend"
// @Success      200  {object}  oscomp.DiskBenchmarkResp
// @Router       /os/disk-benchmark [post]
func NewDiskBenchmarkCommand() *cobra.Command {
	act := DiskBenchmarkAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "disk-benchmark",
		Short: "执行磁盘性能压测 (文件模式 only, 输出 BaselineDisk 兼容字段)",
		Example: fmt.Sprintf(
			`dbactuator os disk-benchmark %s %s`,
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

// Init 反序列化 payload
func (d *DiskBenchmarkAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil {
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Validate basic option validation (具体业务校验在 Comp.Start 里做)
func (d *DiskBenchmarkAct) Validate() error {
	return nil
}

// Run 执行压测
func (d *DiskBenchmarkAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "执行磁盘压测",
			Func:    d.Payload.Start,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("disk-benchmark done")
	return nil
}
