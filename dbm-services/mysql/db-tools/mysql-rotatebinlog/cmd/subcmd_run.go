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
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
)

var runCmd = &cobra.Command{
	Use:          "run",
	Short:        "run rotatebinlog main",
	Long:         `rotate binlog files and backup them to remote backup system`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		configFile := viper.GetString("config")
		comp := rotate.RotateBinlogComp{Config: configFile}
		if err = log.InitLogger(); err != nil {
			return err
		}
		if comp.ConfigObj, err = rotate.InitConfig(configFile); err != nil {
			return err
		}
		return comp.Start()
	},
	PreRun: func(cmd *cobra.Command, args []string) {
	},
}

func init() {
	rootCmd.AddCommand(runCmd)
}
