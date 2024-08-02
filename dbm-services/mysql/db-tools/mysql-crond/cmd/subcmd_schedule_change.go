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
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
)

// versionCmd represents the version command
var changeJobCmd = &cobra.Command{
	Use:   "change-job",
	Short: "change job schedule time ",
	Long:  `change job schedule time `,
	RunE: func(cmd *cobra.Command, args []string) error {

		if jobName, _ := cmd.Flags().GetString("name"); jobName != "" {
			return changeEntry(cmd, jobName)
		}
		return nil
	},
}

func init() {
	changeJobCmd.Flags().StringP("name", "n", "", "full job name")
	changeJobCmd.Flags().StringP("schedule", "s", "", "schedule format like crontab")
	changeJobCmd.Flags().Bool("permanent", false, "permanent schedule to config file, default false")
	changeJobCmd.MarkFlagRequired("name")
	changeJobCmd.MarkFlagRequired("schedule")
	changeJobCmd.MarkFlagRequired("permanent")
	rootCmd.AddCommand(changeJobCmd)
}

func changeEntry(cmd *cobra.Command, jobName string) error {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	schedule, _ := cmd.Flags().GetString("schedule")
	permanent, _ := cmd.Flags().GetBool("permanent")
	configFile, _ := cmd.Flags().GetString("config")
	if apiUrl, err = config.GetApiUrlFromConfig(configFile); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	manager := api.NewManager(apiUrl)
	_, err = manager.ScheduleChange(jobName, schedule, permanent)
	if err != nil {
		return err
	}
	return nil
}
