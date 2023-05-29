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
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
)

// versionCmd represents the version command
var disableJobCmd = &cobra.Command{
	Use:   "disableJob",
	Short: "disable crond entry",
	Long:  `disable crond entry`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var jobEntry api.JobDefine
		if body, _ := cmd.Flags().GetString("body"); body != "" {
			if err := json.Unmarshal([]byte(body), &jobEntry); err != nil {
				return err
			}
		} else {
			jobName, _ := cmd.Flags().GetString("name")
			jobEntry = api.JobDefine{
				Name: jobName,
			}
		}
		return disableEntry(jobEntry)
	},
}

func init() {
	disableJobCmd.PersistentFlags().StringP("config", "c", "", "config file")
	_ = disableJobCmd.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("disable-config", disableJobCmd.PersistentFlags().Lookup("config"))

	disableJobCmd.Flags().StringP("name", "n", "", "name")
	disableJobCmd.Flags().Bool("permanent", false, "permanent disable, default false")
	_ = delJobCmd.MarkFlagRequired("name")

	rootCmd.AddCommand(disableJobCmd)
}

func disableEntry(entry api.JobDefine) error {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	if apiUrl, err = config.GetApiUrlFromConfig(viper.GetString("disable-config")); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	manager := api.NewManager(apiUrl)
	//logger.Info("removing job_item to crond: %+v", jobItem)
	_, err = manager.Disable(entry.Name, true)
	if err != nil {
		return err
	}
	return nil
}
