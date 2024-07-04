/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"errors"
	"fmt"
	"log"
	"log/slog"
	"strings"
	"time"

	"dbm-services/mysql/db-partition/util"

	"dbm-services/mysql/db-partition/model"

	"github.com/robfig/cron/v3"
	"github.com/spf13/viper"
)

// CronList 定时任务列表
var CronList []*cron.Cron

// RegisterCron 注册定时任务
func RegisterCron() ([]*cron.Cron, error) {
	// 每日首次执行分区
	timingHour := viper.GetString("cron.timing_hour")
	// 重试失败的分区规则
	retryHour := viper.GetString("cron.retry_hour")
	if timingHour == "" || retryHour == "" {
		err := errors.New("cron.partition_hour or cron.retry_hour was not set")
		slog.Error("msg", "cron error", err)
		return CronList, err
	}
	timing := fmt.Sprintf("02 %s * * * ", timingHour)
	// 可以配置每日多次重试
	multiHours, errOuter := util.SplitName(retryHour)
	if errOuter != nil {
		errOuter = errors.New("cron.retry_hour format error")
		slog.Error("msg", "cron error", errOuter)
		return CronList, errOuter
	}
	var debug bool
	if strings.ToLower(strings.TrimSpace(viper.GetString("log.level"))) == "debug" {
		debug = true
	}
	timezone := map[string]int{
		"UTC": 0, "UTC+1": 1, "UTC+2": 2, "UTC+3": 3, "UTC+4": 4, "UTC+5": 5, "UTC+6": 6, "UTC+7": 7, "UTC+8": 8,
		"UTC+9": 9, "UTC+10": 10, "UTC+11": 11, "UTC+12": 12, "UTC-11": -11, "UTC-10": -10, "UTC-9": -9,
		"UTC-8": -8, "UTC-7": -7, "UTC-6": -6, "UTC-5": -5, "UTC-4": -4, "UTC-3": -3, "UTC-2": -2, "UTC-1": -1,
	}
	// 为每个时区的分区规则创建对应的定时任务
	for name, offset := range timezone {
		offetSeconds := offset * 60 * 60
		zone := time.FixedZone(name, offetSeconds)
		var c *cron.Cron
		if debug {
			c = cron.New(cron.WithLocation(zone), cron.WithLogger(cron.VerbosePrintfLogger(log.New(model.NewWriter(
				"log/cron.log"), fmt.Sprintf("timezone: %+03d:00  ", offset), log.LstdFlags))))
		} else {
			c = cron.New(cron.WithLocation(zone))
		}
		// 添加执行分区的定时任务
		_, err := c.AddJob(timing, PartitionJob{CronType: Daily, ZoneOffset: offset, ZoneName: name, Hour: timingHour})
		if err != nil {
			slog.Error("msg", "cron add daily job error", err)
			return CronList, err
		}
		for _, retry := range multiHours {
			_, err = c.AddJob(fmt.Sprintf("08 %s * * * ", retry), PartitionJob{CronType: Retry,
				ZoneOffset: offset, ZoneName: name, Hour: retry})
		}
		if err != nil {
			slog.Error("msg", "cron add retry job error", err)
			return CronList, err
		}
		// 启动分区定时任务
		c.Start()
		slog.Info("msg", zone, c.Entries())
		CronList = append(CronList, c)
	}
	return CronList, nil
}
