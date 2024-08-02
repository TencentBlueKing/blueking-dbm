/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package config

import (
	"log/slog"
	"sync"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"
)

// ScheduleJob 调度 job 的 job
// 用于一次调度另一个 job. 主要是明确定义一个 job 类型，便于展示暂停的 job 列表(disabledJobs 里没法知道NextTime)
type ScheduleJob struct {
	originalJob ExternalJob
	WrappedJob  ExternalJob

	cronObj *cron.Cron

	disabledJobs *sync.Map

	onceExecuted bool
}

// Run run once
func (j *ScheduleJob) Run() {
	if j.onceExecuted {
		return
	}
	j.onceExecuted = true
	//j.cronObj.Remove(j.scheduleId)
	if _, exists := j.disabledJobs.LoadAndDelete(j.originalJob.Name); exists {
		slog.Info("pause resume job", slog.String("name", j.originalJob.Name))
		*j.originalJob.Enable = true
		_, _ = j.cronObj.AddJob(j.originalJob.Schedule, &j.originalJob)
	} else {
		// maybe enabled by api
		slog.Warn("pause resume job not exists in disabled list", slog.String("name", j.originalJob.Name))
	}
}

// NewScheduleJob init a scheduled job
func NewScheduleJob(originalJob *ExternalJob, cronObj *cron.Cron, disabledJobs *sync.Map) (*ScheduleJob, error) {
	if originalJob.Name == "" || cronObj == nil || disabledJobs == nil {
		return nil, errors.New("init failed")
	}
	/* else if _, err := cron.Parse(job.Schedule); err != nil  {
		return nil, errors.New("invalid schedule")
	}*/
	j := &ScheduleJob{
		originalJob: *originalJob,
	}
	_ = copier.Copy(&j.WrappedJob, originalJob)
	j.WrappedJob.Name += PauseJobSuffix
	// j.WrappedJob.Command = "Resume: " + j.WrappedJob.Command

	j.cronObj = cronObj
	j.disabledJobs = disabledJobs
	return j, nil
}

const PauseJobSuffix = "@@PAUSE"
