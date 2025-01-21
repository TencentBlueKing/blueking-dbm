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
var enableJobCmd = &cobra.Command{
	Use:   "enable-job",
	Short: "enable crond entry",
	Long:  `enable crond entry`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return enableEntry(cmd)
	},
}

func init() {
	enableJobCmd.Flags().StringP("name", "n", "", "full job name")
	enableJobCmd.Flags().StringP("name-match", "m", "", "name-match using regex")
	enableJobCmd.Flags().Bool("permanent", false, "permanent enable to config file, default false")
	enableJobCmd.MarkFlagsOneRequired("name", "name-match")
	enableJobCmd.MarkFlagsMutuallyExclusive("name", "name-match")
	rootCmd.AddCommand(enableJobCmd)
}

// enableEntry 启用当前是 disabled 状态的entry
// 没有找到 entry 返回 nil
func enableEntry(cmd *cobra.Command) error {
	var jobNames []string
	permanent, _ := cmd.Flags().GetBool("permanent")
	if jobName, _ := cmd.Flags().GetString("name"); jobName != "" {
		jobNames = append(jobNames, jobName)
		return enableEntryByNames(cmd, jobNames, permanent)
	} else if nameMatch, _ := cmd.Flags().GetString("name-match"); nameMatch != "" {
		entries := listEntries(cmd, api.JobStatusDisabled)
		if len(entries) == 0 {
			return nil
			//return errors.Errorf("no job match %s", nameMatch)
		}
		for _, entry := range entries {
			jobNames = append(jobNames, entry.Job.Name)
		}
		return enableEntryByNames(cmd, jobNames, permanent)
	}
	return nil
}

// enableEntryByNames resume
func enableEntryByNames(cmd *cobra.Command, jobNames []string, permanent bool) error {
	var err error
	apiUrl := ""
	configFile, _ := cmd.Flags().GetString("config")
	if apiUrl, err = config.GetApiUrlFromConfig(configFile); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	manager := api.NewManager(apiUrl)
	for _, name := range jobNames {
		_, err = manager.Resume(name, permanent)
		if err != nil {
			return err
		}
	}
	return nil
}
