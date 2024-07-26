/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmd

import (
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	loadPhysicalCmd.Flags().String("defaults-file", "", "Database to dump, default all")
	loadPhysicalCmd.Flags().Bool("copy-back", false, "tables to dump, comma separated, default all")

	viper.BindPFlag("PhysicalLoad.DefaultsFile", loadPhysicalCmd.Flags().Lookup("databases"))
	viper.BindPFlag("PhysicalLoad.CopyBack", loadPhysicalCmd.Flags().Lookup("tables"))
}

var loadPhysicalCmd = &cobra.Command{
	Use:          "physical",
	Short:        "physical recover using xtrabackup",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", cst.DbbackupGoInstallPath)
		}()
		cnf, err := initLoadCmd(cmd)
		if err != nil {
			return err
		}
		err = loadData(cnf, cst.BackupPhysical)
		if err != nil {
			logger.Log.Error("Load Dbbackup: Failure")
			return errors.WithMessage(err, "load data physical")

		}
		return nil
	},
}
