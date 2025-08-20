// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	errs "errors"
	"fmt"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// versionCmd represents the version command
var subCmdReschedule = &cobra.Command{
	Use:   "reschedule",
	Short: "reschedule",
	Long:  `reschedule`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return handleScheduler(cmd)
	},
}

func init() {
	subCmdReschedule.Flags().StringP("config", "c", "", "config files to backup")
	subCmdReschedule.Flags().Bool("remove", false, "remove backup jobs from mysql-crond")
	subCmdReschedule.Flags().String("cluster-type", "", "cluster type: tendbcluster,tendbha,tendbsingle")
	subCmdReschedule.MarkFlagRequired("config")
	rootCmd.AddCommand(subCmdReschedule)
}

func handleScheduler(cmd *cobra.Command) (err error) {
	confFile, _ := cmd.Flags().GetString("config")
	delSchedule, _ := cmd.Flags().GetBool("remove")

	var cnf = config.BackupConfig{}
	viper.SetConfigType("ini")
	viper.SetConfigFile(confFile)
	if err = viper.ReadInConfig(); err != nil {
		return err
	}
	if err = viper.Unmarshal(&cnf); err != nil {
		return err
	}
	clusterType, _ := cmd.Flags().GetString("cluster-type")
	if clusterType == "" && strings.HasPrefix(cnf.Public.ClusterAddress, "spider.") {
		clusterType = "tendbcluster"
	}

	defaultJobs := config.NewDefaultBackupSchedule()
	if delSchedule == true {
		for jobName, job := range defaultJobs {
			crondManager := ma.NewManager(job.MysqlCrondUrl)
			_, err1 := crondManager.Delete(jobName, true)
			if err1 != nil {
				if strings.Contains(err1.Error(), "not found") {
					continue
				}
				err = errs.Join(err, err1)
			}
		}
		return err
	}
	// spider集群: spider: spiderbackup-schedule, spiderbackup-check
	// tendb 集群: dbbackup-schedule
	if strings.EqualFold(clusterType, "tendbcluster") {
		remoteSchedule := defaultJobs["spiderbackup-check"]
		if !(strings.EqualFold(cnf.Public.MysqlRole, cst.BackupRoleSpiderMnt) ||
			strings.EqualFold(cnf.Public.MysqlRole, cst.BackupRoleSpiderSlave)) {
			if err = addSchedule(remoteSchedule.MysqlCrondUrl, remoteSchedule); err != nil {
				return err
			}
		}

		if strings.EqualFold(cnf.Public.MysqlRole, cst.BackupRoleSpiderMaster) {
			// tendbcluster 集群的 CronTime 只对 spider 节点有用
			if cnf.Schedule.CronTime == "" {
				cnf.Schedule = *defaultJobs["spiderbackup-check"]
			} else {
				cnf.Schedule = *initScheduleWithDefault(cnf.Schedule, "spiderbackup-check")
			}
			if !strings.HasPrefix(cnf.Schedule.JobName, "spiderbackup") {
				return errors.Errorf("%s is a tendbcluster, JobName should start with spiderbackup",
					cnf.Public.ClusterAddress)
			}
			// spider 节点要同时注册 spiderbackup-schedule,spiderbackup-check
			if err = addSchedule(cnf.Schedule.MysqlCrondUrl, &cnf.Schedule); err != nil {
				return err
			}
		}
		return nil
	} else {
		// tendbha: backend
		if cnf.Schedule.CronTime == "" {
			cnf.Schedule = *defaultJobs["dbbackup-schedule"]
		} else {
			cnf.Schedule = *initScheduleWithDefault(cnf.Schedule, "dbbackup-schedule")
		}
		if !strings.HasPrefix(cnf.Schedule.JobName, "dbbackup") {
			return errors.Errorf("%s is a tendb, JobName should start with dbbackup",
				cnf.Public.ClusterAddress)
		}
		return addSchedule(cnf.Schedule.MysqlCrondUrl, &cnf.Schedule)
	}
}

func initScheduleWithDefault(schedule config.Schedule, jobName string) *config.Schedule {
	defaultJobs := config.NewDefaultBackupSchedule()
	if schedule.JobName == "" {
		schedule.JobName = (*defaultJobs[jobName]).JobName
	}
	if schedule.Command == "" {
		schedule.Command = (*defaultJobs[jobName]).Command
		schedule.Args = (*defaultJobs[jobName]).Args
	}
	if schedule.MysqlCrondUrl == "" {
		schedule.MysqlCrondUrl = (*defaultJobs[jobName]).MysqlCrondUrl
	}
	return &schedule
}

func addSchedule(apiUrl string, schedule *config.Schedule) error {
	if schedule.JobName == "" {
		return errors.Errorf("JobName is empty")
	}
	crondManager := ma.NewManager(apiUrl)
	jobItem := ma.JobDefine{
		Name:     schedule.JobName,
		Command:  schedule.Command,
		Args:     strings.Split(schedule.Args, " "),
		Schedule: schedule.CronTime,
		WorkDir:  cst.DbbackupGoInstallPath,
		Creator:  "sys",
		Enable:   true,
	}
	fmt.Printf("adding job_item to crond: %+v\n", jobItem)
	_, err := crondManager.CreateOrReplace(jobItem, true)
	if err != nil {
		return err
	}
	return nil
}
