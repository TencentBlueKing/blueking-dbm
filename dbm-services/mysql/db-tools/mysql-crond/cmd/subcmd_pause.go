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
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
)

// versionCmd represents the version command
var pauseJobCmd = &cobra.Command{
	Use:   "pause-job",
	Short: "pause crond entry",
	Long:  `pause crond entry`,
	RunE: func(cmd *cobra.Command, args []string) error {
		rewrite, _ := cmd.Flags().GetBool("rewrite")
		if rewrite {
			// permanent is always false
			if err := enableEntry(cmd); err != nil {
				return errors.WithMessage(err, "enable entry first")
			}
		}
		return pauseEntry(cmd)
	},
}

func init() {
	pauseJobCmd.Flags().StringP("name", "n", "", "full job name")
	pauseJobCmd.Flags().StringP("name-match", "m", "", "name-match using regex")
	pauseJobCmd.Flags().DurationP("duration", "r", 1*time.Hour, "pause job duration， default 1h")
	pauseJobCmd.Flags().Bool("rewrite", false, "if one entry is disabled before, rewrite with new duration")
	pauseJobCmd.MarkFlagsOneRequired("name", "name-match")
	pauseJobCmd.MarkFlagsMutuallyExclusive("name", "name-match")
	rootCmd.AddCommand(pauseJobCmd)
}

func pauseEntry(cmd *cobra.Command) error {
	var jobNames []string
	dura, _ := cmd.Flags().GetDuration("duration")
	if jobName, _ := cmd.Flags().GetString("name"); jobName != "" {
		jobNames = append(jobNames, jobName)
		return pauseEntryByNames(cmd, jobNames, dura)
	} else if nameMatch, _ := cmd.Flags().GetString("name-match"); nameMatch != "" {
		entries := listEntries(cmd, api.JobStatusEnabled)
		if len(entries) == 0 {
			return nil
			//return errors.Errorf("no job match %s", nameMatch)
		}
		for _, entry := range entries {
			jobNames = append(jobNames, entry.Job.Name)
		}
		return pauseEntryByNames(cmd, jobNames, dura)
	}
	return nil
}

// pauseEntryByNames pauseEntryByNames
func pauseEntryByNames(cmd *cobra.Command, jobNames []string, dura time.Duration) error {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	configFile, _ := cmd.Flags().GetString("config")
	if apiUrl, err = config.GetApiUrlFromConfig(configFile); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	manager := api.NewManager(apiUrl)
	for _, name := range jobNames {
		_, err = manager.Pause(name, dura)
		if err != nil {
			return err
		}
	}
	return nil
}
