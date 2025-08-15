// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// Schedule 备份定时任务
type Schedule struct {
	JobName       string `ini:"JobName"`
	CronTime      string `ini:"CronTime"`
	Command       string `ini:"Command"`
	Args          string `ini:"-"`
	MysqlCrondUrl string `ini:"-"`
}

// NewDefaultBackupSchedule 默认备份定时任务：三类
func NewDefaultBackupSchedule() map[string]*Schedule {
	backendSchedule := &Schedule{
		CronTime:      "0 3 * * *",
		Command:       filepath.Join(cst.DbbackupGoInstallPath, "dbbackup_main.sh"),
		Args:          "",
		JobName:       "dbbackup-schedule",
		MysqlCrondUrl: "http://127.0.0.1:9999",
	}
	remoteSchedule := &Schedule{
		CronTime:      "*/1 * * * *",
		Command:       filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"), // ./dbbackup spiderbackup check -run
		Args:          "spiderbackup check --run",
		JobName:       "spiderbackup-check",
		MysqlCrondUrl: "http://127.0.0.1:9999",
	}
	spiderSchedule := &Schedule{
		CronTime:      "0 3 * * *",
		Command:       filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"), // ./dbbackup spiderbackup schedule
		Args:          "spiderbackup schedule",
		JobName:       "spiderbackup-schedule",
		MysqlCrondUrl: "http://127.0.0.1:9999",
	}
	var sches = map[string]*Schedule{
		"spiderbackup-check":    remoteSchedule,
		"spiderbackup-schedule": spiderSchedule,
		"dbbackup-schedule":     backendSchedule,
	}
	return sches
}
