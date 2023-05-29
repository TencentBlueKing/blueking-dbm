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
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
)

var crondCmd = &cobra.Command{
	Use:   "crond",
	Short: "schedule operation",
	Long:  `add or remove items from mysql-crond`,
	RunE: func(cmd *cobra.Command, args []string) error {
		comp := rotate.RotateBinlogComp{Config: viper.GetString("config")}

		addSchedule, _ := cmd.Flags().GetBool("add")
		delSchedule, _ := cmd.Flags().GetBool("remove")
		if isSchedule, err := comp.HandleScheduler(addSchedule, delSchedule); err != nil {
			return err
		} else if isSchedule {
			return nil
		}
		return nil
	},
}

func init() {
	//命令行的flag
	crondCmd.Flags().Bool("add", false, "add schedule to crond")
	crondCmd.Flags().Bool("remove", false, "del schedule from crond")

	rootCmd.AddCommand(crondCmd)
}
