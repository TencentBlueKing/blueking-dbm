/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cron

import (
	"fmt"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
	"dbm-services/mysql/db-partition/service"
	"dbm-services/mysql/db-partition/util"

	"golang.org/x/exp/slog"
)

// Scheduler TODO
var Scheduler string

// Run TODO
func (m PartitionJob) Run() {
	var err error
	Scheduler, err = util.ExecShellCommand(false, "hostname -I")
	if err != nil {
		Scheduler = "0.0.0.0"
	}
	if m.CronType == Heartbeat {
		monitor.SendMetric(Scheduler)
		return
	}
	key := fmt.Sprintf("%s_%d_%s", m.CronType, m.ZoneOffset, m.CronDate)
	model.Lock(key)
	m.ExecutePartitionCron(service.Tendbha)
	m.ExecutePartitionCron(service.Tendbcluster)
	flag, err := model.Lock(key)
	if err != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. set redis mutual exclusion error: %s", err.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "model.Lock err", err)
	} else if flag {
		m.ExecutePartitionCron(service.Tendbha)
		m.ExecutePartitionCron(service.Tendbcluster)
	} else {
		slog.Warn("set redis mutual exclusion fail, do nothing", "key", key)
	}
}

// ExecutePartitionCron 执行所有业务的分区
func (m PartitionJob) ExecutePartitionCron(clusterType string) {
	zone := fmt.Sprintf("%+03d:00", m.ZoneOffset)
	needMysql, errOuter := service.NeedPartition(m.CronType, clusterType, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. get need partition list fail: %s", errOuter.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "get need partition list fail", errOuter)
		return
	}
	for _, item := range needMysql {
		objects, err := (*item).DryRun()
		if err != nil {
			code, _ := errno.DecodeErr(err)
			if code == errno.NothingToDo.Code {
				service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
					item.ImmuteDomain, zone, m.CronDate, Scheduler, "{}",
					errno.NothingToDo.Message, service.CheckSucceeded, item.ClusterType)
				continue
			} else {
				dimension := monitor.NewPartitionEventDimension(item.BkBizId, *item.BkCloudId, item.ImmuteDomain)
				content := fmt.Sprintf("partition error. get partition sql fail: %s", err.Error())
				monitor.SendEvent(monitor.PartitionEvent, dimension, content, "0.0.0.0")
				service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
					item.ImmuteDomain, zone, m.CronDate, Scheduler, "{}",
					content, service.CheckFailed, item.ClusterType)
				slog.Error(fmt.Sprintf("%v", *item), "get partition sql fail", err)
				continue
			}
		}
		service.CreatePartitionTicket(*item, objects, m.ZoneOffset, m.CronDate, Scheduler)
	}
}
