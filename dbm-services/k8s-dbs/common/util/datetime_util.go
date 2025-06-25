/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package util

import (
	"fmt"
	"time"
)

// 常量定义常用的日期时间格式
const (
	LayoutRFC3339         = time.RFC3339                // RFC3339 格式
	LayoutISO8601         = "2006-01-02T15:04:05Z07:00" // ISO8601 格式
	LayoutYYYYMMDD        = "2006-01-02"                // 年-月-日 格式
	LayoutYYYYMMDDHHMM    = "2006-01-02 15:04"          // 年-月-日 时:分 格式
	LayoutYYYYMMDDHHMMSS  = "2006-01-02 15:04:05"       // 年-月-日 时:分:秒 格式
	LayoutYYYYMMDDHHMMSSZ = "2006-01-02 15:04:05Z"      // 年-月-日 时:分:秒 Z 格式
	LayoutUnixTimestamp   = "1136239445"                // Unix 时间戳（秒）
)

// Now 返回当前时间的字符串表示，如果 format 为空，则使用 RFC3339 格式
func Now(format string) string {
	if format == "" {
		return time.Now().Format(LayoutRFC3339)
	}
	return time.Now().Format(format)
}

// Parse 将时间字符串解析为 time.Time 对象，如果 format 为空，则使用 RFC3339 格式
// 如果 timeStr 为空，返回错误
func Parse(timeStr, format string) (time.Time, error) {
	if timeStr == "" {
		return time.Time{}, fmt.Errorf("空的时间字符串")
	}
	if format == "" {
		return time.Parse(LayoutRFC3339, timeStr)
	}
	return time.Parse(format, timeStr)
}

// Format 将 time.Time 对象格式化为字符串，如果 format 为空，则使用 RFC3339 格式
func Format(t time.Time, format string) string {
	if format == "" {
		return t.Format(LayoutRFC3339)
	}
	return t.Format(format)
}

// Diff 计算两个时间之间的差值，并返回秒、分钟、小时和天的差值
// 确保 t1 <= t2
func Diff(t1, t2 time.Time) (seconds, minutes, hours, days int64) {
	if t1.After(t2) {
		t1, t2 = t2, t1 // 确保 t1 <= t2
	}
	diff := t2.Sub(t1)
	seconds = int64(diff.Seconds())
	minutes = seconds / 60
	hours = minutes / 60
	days = hours / 24
	return seconds, minutes, hours, days
}

// Add 给 time.Time 对象添加一个时间间隔，并返回新的时间
func Add(t time.Time, duration time.Duration) time.Time {
	return t.Add(duration)
}

// Sub 从 time.Time 对象中减去一个时间间隔，并返回新的时间
func Sub(t time.Time, duration time.Duration) time.Time {
	return t.Add(-duration)
}

// UnixTimestamp 返回当前时间的 Unix 时间戳（秒）
func UnixTimestamp() int64 {
	return time.Now().Unix()
}

// UnixTimestampMillis 返回当前时间的 Unix 时间戳（毫秒）
func UnixTimestampMillis() int64 {
	return time.Now().UnixMilli()
}

// UnixTimestampMicro 返回当前时间的 Unix 时间戳（微秒）
func UnixTimestampMicro() int64 {
	return time.Now().UnixMicro()
}

// FromUnixTimestamp 将 Unix 时间戳（秒）转换为 time.Time 对象
func FromUnixTimestamp(timestamp int64) time.Time {
	return time.Unix(timestamp, 0)
}

// FromUnixTimestampMillis 将 Unix 时间戳（毫秒）转换为 time.Time 对象
func FromUnixTimestampMillis(timestamp int64) time.Time {
	return time.UnixMilli(timestamp)
}

// FromUnixTimestampMicro 将 Unix 时间戳（微秒）转换为 time.Time 对象
func FromUnixTimestampMicro(timestamp int64) time.Time {
	return time.UnixMicro(timestamp)
}

// IsZero 检查 time.Time 对象是否为零值（即未设置）
func IsZero(t time.Time) bool {
	return t.IsZero()
}

// StartOfDay 返回当天的开始时间（00:00:00）
func StartOfDay(t time.Time) time.Time {
	year, month, day := t.Date()
	return time.Date(year, month, day, 0, 0, 0, 0, t.Location())
}

// EndOfDay 返回当天的结束时间（23:59:59.999999999）
func EndOfDay(t time.Time) time.Time {
	year, month, day := t.Date()
	return time.Date(year, month, day, 23, 59, 59, int(time.Second-time.Nanosecond), t.Location())
}

// IsWeekend 判断给定时间是否是周末（周六或周日）
func IsWeekend(t time.Time) bool {
	weekday := t.Weekday()
	return weekday == time.Saturday || weekday == time.Sunday
}

// NextWorkday 返回当前时间的下一个工作日（跳过周末）
func NextWorkday(t time.Time) time.Time {
	for {
		t = t.AddDate(0, 0, 1)
		if !IsWeekend(t) {
			return t
		}
	}
}
