/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package crond

import (
	"log/slog"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
)

// ScheduleChange 修改 job 的 schedule 时间
// return new entry id
func ScheduleChange(j *config.ExternalJob, permanent bool) (int, error) {
	existEntry := findEntry(j.Name)
	if existEntry == nil {
		err := errors.WithMessagef(api.NotFoundError, "change [%s] schedule time", j.Name)
		slog.Error("change schedule", slog.String("error", err.Error()))
		return 0, err
	}
	existJob := existEntry.Job.(*config.ExternalJob)
	newJob := &config.ExternalJob{}
	if err := copier.Copy(newJob, existJob); err != nil {
		return 0, err
	}
	newJob.Schedule = j.Schedule
	if _, err := deleteActivate(existEntry, permanent); err != nil {
		return 0, err
	}
	if *newJob.Enable {
		return addActivate(newJob, permanent)
	} else {
		return addDisabled(newJob, permanent)
	}
}
