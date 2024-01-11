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
	"log/slog"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
	"dbm-services/mysql/db-partition/service"
)

// Scheduler TODO
var Scheduler string

// Run TODO
func (m PartitionJob) Run() {
	var err error
	var key string
	Scheduler = "127.0.0.1"
	offetSeconds := m.ZoneOffset * 60 * 60
	zone := time.FixedZone(m.ZoneName, offetSeconds)
	m.CronDate = time.Now().In(zone).Format("20060102")
	key = fmt.Sprintf("%s_%s_%d_%s", m.CronType, m.Hour, m.ZoneOffset, m.CronDate)
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
				// 当天首次执行发现没有需要执行的sql，记录日志。重试没有执行的sql，不需要记录日志。
				if m.CronType == "daily" {
					_ = service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
						item.ImmuteDomain, zone, m.CronDate, Scheduler, errno.NothingToDo.Message, service.CheckSucceeded,
						item.ClusterType)
				}
				continue
			} else {
				dimension := monitor.NewPartitionEventDimension(item.BkBizId, *item.BkCloudId, item.ImmuteDomain)
				content := fmt.Sprintf("partition error. get partition sql fail: %s", err.Error())
				monitor.SendEvent(monitor.PartitionEvent, dimension, content, "127.0.0.1")
				_ = service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
					item.ImmuteDomain, zone, m.CronDate, Scheduler, content, service.CheckFailed, item.ClusterType)
				slog.Error(fmt.Sprintf("%v", *item), "get partition sql fail", err)
				continue
			}
		}
		slog.Info("do create partition ticket")
		service.CreatePartitionTicket(*item, objects, m.ZoneOffset, m.CronDate, Scheduler)
	}
}
