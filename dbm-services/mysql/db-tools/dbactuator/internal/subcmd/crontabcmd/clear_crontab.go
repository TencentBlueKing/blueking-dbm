/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package crontabcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/crontab"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// ClearCrontabAct 清理定时任务
type ClearCrontabAct struct {
	*subcmd.BaseOptions
	Service crontab.ClearCrontabParam
}

// ClearCrontabCommand 清理定时任务
func ClearCrontabCommand() *cobra.Command {
	act := ClearCrontabAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "clear-crontab",
		Short:   "清理crontab",
		Example: fmt.Sprintf(`dbactuator clear-crontab %s`, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化
func (s *ClearCrontabAct) Init() (err error) {
	if err = s.Deserialize(&s.Service); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run 执行
func (s *ClearCrontabAct) Run() (err error) {
	steps := []subcmd.StepFunc{
		{
			FunName: "清理机器的crontab",
			Func:    s.Service.CleanCrontab,
		},
		{
			FunName: "清理机器周边目录",
			Func:    s.Service.CleanDBToolsFolder,
		},
	}
	logger.Info("start clean crontab ...")
	for idx, f := range steps {
		if err = f.Func(); err != nil {
			logger.Error("step <%d>, run [%s] occur %v", idx, f.FunName, err)
			return err
		}
		logger.Info("step <%d>, run [%s] successfully", idx, f.FunName)
	}
	logger.Info("clean crontab successfully")
	return
}
