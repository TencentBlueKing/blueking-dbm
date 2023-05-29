/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sysinitcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/sysinit"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// SysInitAct TODO
type SysInitAct struct {
	*subcmd.BaseOptions
	Service sysinit.SysInitParam
}

// NewSysInitCommand TODO
func NewSysInitCommand() *cobra.Command {
	act := SysInitAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "sysinit",
		Short:   "Exec sysinit_mysql.sh,Init mysql default os user,password",
		Example: `dbactuator sysinit -p eyJ1c2VyIjoiIiwicHdkIjoiIn0=`,
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *SysInitAct) Init() (err error) {
	if err = d.DeserializeNonStandard(&d.Service); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run TODO
func (s *SysInitAct) Run() (err error) {
	steps := []subcmd.StepFunc{
		{
			FunName: "执行sysInit脚本",
			Func:    s.Service.SysInitMachine,
		},
	}
	steps = append(
		steps, subcmd.StepFunc{
			FunName: fmt.Sprintf("重置%sOS密码", s.Service.OsMysqlUser),
			Func:    s.Service.SetOsPassWordForMysql,
		},
	)

	logger.Info("start sysinit ...")
	for idx, f := range steps {
		if err = f.Func(); err != nil {
			logger.Error("step <%d>, run [%s] occur %v", idx, f.FunName, err)
			return err
		}
		logger.Info("step <%d>, run [%s] successfully", idx, f.FunName)
	}
	logger.Info("sysinit successfully")
	return
}
