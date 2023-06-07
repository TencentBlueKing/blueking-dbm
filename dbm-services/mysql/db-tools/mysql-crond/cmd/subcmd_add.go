/*
 * Tencent is pleased to support the open source community by making Blueking Container Service available.
 * Copyright (C) 2019 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 * http://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
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
var addJobCmd = &cobra.Command{
	Use:   "addJob",
	Short: "add crond entry",
	Long:  `add crond entry`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var jobEntry api.JobDefine
		if body, _ := cmd.Flags().GetString("body"); body != "" {
			if err := json.Unmarshal([]byte(body), &jobEntry); err != nil {
				return err
			}
		} else {
			jobName, _ := cmd.Flags().GetString("name")
			jobCommand, _ := cmd.Flags().GetString("command")
			jobArgs, _ := cmd.Flags().GetStringSlice("args")
			jobSchedule, _ := cmd.Flags().GetString("schedule")
			jobWorkDir, _ := cmd.Flags().GetString("work_dir")
			jobCreator, _ := cmd.Flags().GetString("creator")
			jobEnable, _ := cmd.Flags().GetBool("enable")
			jobEntry = api.JobDefine{
				Name:     jobName,
				Command:  jobCommand,
				Args:     jobArgs,
				Schedule: jobSchedule,
				WorkDir:  jobWorkDir,
				Creator:  jobCreator,
				Enable:   jobEnable,
			}
		}
		return addEntry(jobEntry)
	},
}

func init() {
	addJobCmd.PersistentFlags().StringP("config", "c", "", "config file")
	_ = addJobCmd.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("add-config", addJobCmd.PersistentFlags().Lookup("config"))

	addJobCmd.Flags().StringP("name", "n", "", "name")
	addJobCmd.Flags().StringP("command", "m", "", "command")
	addJobCmd.Flags().StringSliceP("args", "a", []string{}, "args, comma separate")
	addJobCmd.Flags().StringP("schedule", "s", "", "schedule")
	addJobCmd.Flags().StringP("work_dir", "d", "", "work dir")
	addJobCmd.Flags().StringP("creator", "r", "", "creator")
	addJobCmd.Flags().BoolP("enable", "e", true, "enable")
	addJobCmd.Flags().String("body", "", "json body for api /create_or_replace")
	addJobCmd.MarkFlagsMutuallyExclusive("command", "body")
	addJobCmd.MarkFlagsMutuallyExclusive("name", "body")

	rootCmd.AddCommand(addJobCmd)
}

func addEntry(entry api.JobDefine) error {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	if apiUrl, err = config.GetApiUrlFromConfig(viper.GetString("add-config")); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	manager := api.NewManager(apiUrl)
	//logger.Info("adding job_item to crond: %+v", jobItem)
	_, err = manager.CreateOrReplace(entry, true)
	if err != nil {
		return err
	}
	return nil
}
