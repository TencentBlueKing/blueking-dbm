/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil

import (
	"time"

	"github.com/pkg/errors"
)

// ToDays 计算从公元 0 年到指定日期之间的天数，类似 MySQL 的 TO_DAYS() 函数
// 支持的日期格式: "2017-06-20", "2017-06-20 09:34:00"
// 返回从公元 0 年到指定日期的天数
func ToDays(dateStr string) (int, error) {
	// 支持的日期格式
	formats := []string{
		"2006-01-02",
		"2006-01-02 15:04:05",
	}

	var parsedTime time.Time
	var err error

	// 尝试解析日期字符串
	for _, format := range formats {
		parsedTime, err = time.Parse(format, dateStr)
		if err == nil {
			break
		}
	}

	if err != nil {
		return 0, errors.Wrapf(err, "无法解析日期字符串: %s", dateStr)
	}
	return TimeToDays(parsedTime), nil
}

func MustToDays(dateStr string) int {
	days, err := ToDays(dateStr)
	if err != nil {
		panic(err)
	}
	return days
}

func TimeToDays(t time.Time) int {
	// MySQL TO_DAYS() 的基准日期是公元 0 年
	// MySQL 使用的是 Proleptic Gregorian Calendar
	// 从公元 0 年 1 月 1 日（第 1 天）到公元 1 年 1 月 1 日（第 366 天）有 365 天

	year := t.Year()
	month := int(t.Month())
	day := t.Day()

	// 计算从公元 1 年到目标年份前一年的总天数
	totalDays := 0
	for y := 1; y < year; y++ {
		if isLeapYear(y) {
			totalDays += 366
		} else {
			totalDays += 365
		}
	}

	// 加上当前年份从 1 月 1 日到目标日期的天数
	daysInMonth := []int{0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}
	if isLeapYear(year) {
		daysInMonth[2] = 29
	}

	for m := 1; m < month; m++ {
		totalDays += daysInMonth[m]
	}
	totalDays += day

	// 加上从公元 0 年的天数（365 天）
	totalDays += 365

	return totalDays
}

// isLeapYear 判断是否为闰年（使用格里高利历规则）
func isLeapYear(year int) bool {
	return (year%4 == 0 && year%100 != 0) || (year%400 == 0)
}
