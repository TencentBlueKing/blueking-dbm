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

var instanceCmd = &cobra.Command{
	Use:   "instance",
	Short: "instance config operation",
	Long:  `add or remove instance rotate config(user port), and will reschedule for mysql-crond`,
	RunE: func(cmd *cobra.Command, args []string) error {
		comp := rotate.RotateBinlogComp{Config: viper.GetString("config")}
		if removeConfigs, err := cmd.Flags().GetStringSlice("remove"); err != nil {
			return err
		} else if len(removeConfigs) > 0 {
			if err = comp.RemoveConfig(removeConfigs); err != nil {
				return err
			}
			// if remove success, need to reschedule mysql-rotatebinlog for mysql-crond
			if _, err := comp.HandleScheduler(true, false); err != nil {
				return err
			}
		}
		return nil
	},
}

func init() {
	//命令行的flag
	instanceCmd.Flags().StringSlice("remove", nil, "remove binlog instance rotate port from config")

	rootCmd.AddCommand(instanceCmd)
}
