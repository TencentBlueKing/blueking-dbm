// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlcmd

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/backupdemand"

	"github.com/spf13/cobra"
)

// BackupDemandAct TODO
type BackupDemandAct struct {
	*subcmd.BaseOptions
	Payload backupdemand.Component
}

// NewBackupDemandCommand create new subcommand
func NewBackupDemandCommand() *cobra.Command {
	act := BackupDemandAct{BaseOptions: subcmd.GBaseOptions}
	cmd := &cobra.Command{
		Use:   "backup-demand",
		Short: "备份请求",
		Example: fmt.Sprintf(
			`dbactuator mysql backup-demand %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init prepare run env
func (d *BackupDemandAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	logger.Warn("params %+v", d.Payload.Params)

	return
}

// Validate run selfdefine validate function
func (d *BackupDemandAct) Validate() error {
	return nil
}

// Run start run command
func (d *BackupDemandAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "生成备份配置",
			Func:    d.Payload.GenerateBackupConfig,
		},
		{
			FunName: "执行备份",
			Func:    d.Payload.DoBackup,
		},
		{
			FunName: "返回报告",
			Func:    d.Payload.OutPut,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("backup demand success")
	return nil
}
