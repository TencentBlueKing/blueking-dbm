/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package oscomp OS 层面通用 component (与具体数据库产品无关)
package oscomp

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// DBProcessBlacklist DB 系列进程黑名单。
// 命中其中任一则禁止跑磁盘压测，避免 IO 抢占影响线上服务、或在错误的机器上误操作。
//
// 上线前请与 SRE 一起按当前生产环境校对（特别是蓝鲸 TenDBHA 实际使用的 proxy 进程名、
// Tendis 系命名等可能因部署版本不同而变化）。
var DBProcessBlacklist = []string{
	// MySQL / Spider / TenDBCluster
	"mysqld", "mysqld_safe", "tdbctl",
	// MySQL Proxy (TenDBHA)
	"mysql-proxy",
	// Redis 系
	"redis-server", "redis-sentinel",
	"predixy", "nutcracker", // nutcracker 是 twemproxy 的实际进程名
	"tendisplus", "tendisssd",
	// MongoDB
	"mongod", "mongos",
	// SQLServer (Linux)
	"sqlservr",
}

// ProcessHit 命中黑名单的进程信息
type ProcessHit struct {
	Pid  int    `json:"pid"`
	Comm string `json:"comm"`
}

// ScanDBProcesses 扫 /proc/*/comm，匹配 DB 进程黑名单
// 返回命中的 (pid, comm) 列表; 空列表表示安全
func ScanDBProcesses() ([]ProcessHit, error) {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil, fmt.Errorf("read /proc: %w", err)
	}
	blacklist := make(map[string]struct{}, len(DBProcessBlacklist))
	for _, n := range DBProcessBlacklist {
		blacklist[n] = struct{}{}
	}
	var hits []ProcessHit
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			// /proc 下非纯数字目录跳过 (acpi/sys/...)
			continue
		}
		commPath := filepath.Join("/proc", e.Name(), "comm")
		data, err := os.ReadFile(commPath)
		if err != nil {
			// 进程已退出或权限不足，不视为致命错误
			continue
		}
		comm := strings.TrimSpace(string(data))
		if _, ok := blacklist[comm]; ok {
			hits = append(hits, ProcessHit{Pid: pid, Comm: comm})
		}
	}
	return hits, nil
}

// FormatHitsError 把命中列表格式化为人类可读的拒绝错误
func FormatHitsError(hits []ProcessHit) error {
	lines := make([]string, 0, len(hits))
	for _, h := range hits {
		lines = append(lines, fmt.Sprintf("  pid=%d  %s", h.Pid, h.Comm))
	}
	return fmt.Errorf(
		"拒绝执行: 主机上检测到正在运行的 DB 进程, 不能在此机器跑磁盘压测:\n%s\n请先停止这些服务或换一台空闲机, 再重试",
		strings.Join(lines, "\n"),
	)
}
