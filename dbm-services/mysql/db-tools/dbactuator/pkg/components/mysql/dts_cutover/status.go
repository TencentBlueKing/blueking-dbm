/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// SyncStatus DTS 任务增量同步状态（HTTP status 子集）。
type SyncStatus struct {
	MasterBinlog        string   `json:"master_binlog"`
	MasterBinlogGtid    string   `json:"master_binlog_gtid"`
	SyncerBinlog        string   `json:"syncer_binlog"`
	SyncerBinlogGtid    string   `json:"syncer_binlog_gtid"`
	BlockingDDLs        []string `json:"blocking_ddls"`
	SecondsBehindMaster int      `json:"seconds_behind_master"`
	Synced              bool     `json:"synced"`
}

// TaskStatusItem GET /api/v1/tasks/{task}/status 单条。
type TaskStatusItem struct {
	Name       string      `json:"name"`
	SourceName string      `json:"source_name"`
	Stage      string      `json:"stage"`
	Unit       string      `json:"unit"`
	ErrorMsg   string      `json:"error_msg"`
	SyncStatus *SyncStatus `json:"sync_status"`
}

// TaskStatusListResponse 任务状态列表响应。
type TaskStatusListResponse struct {
	Total int              `json:"total"`
	Data  []TaskStatusItem `json:"data"`
}

// CutoverPositionOutput 供 Flow 落库的位点输出。
type CutoverPositionOutput struct {
	TaskName  string                   `json:"task_name"`
	Sources   []SourcePositionSnapshot `json:"sources"`
	StoppedAt string                   `json:"stopped_at"`
}

// SourcePositionSnapshot 单个 source 的位点快照。
type SourcePositionSnapshot struct {
	SourceName       string `json:"source_name"`
	MasterBinlog     string `json:"master_binlog"`
	MasterBinlogGtid string `json:"master_binlog_gtid"`
	SyncerBinlog     string `json:"syncer_binlog"`
	SyncerBinlogGtid string `json:"syncer_binlog_gtid"`
	SecondsBehind    int    `json:"seconds_behind_master"`
}

// buildMasterAPIURL 拼装 Master OpenAPI URL（本机直连 dts_master_addr）。
func buildMasterAPIURL(dtsMasterAddr, apiPath string) (string, error) {
	addr := strings.TrimSpace(dtsMasterAddr)
	if addr == "" {
		return "", fmt.Errorf("dts_master_addr 为空")
	}
	if !strings.Contains(addr, "://") {
		addr = "http://" + addr
	}
	u, err := url.Parse(addr)
	if err != nil {
		return "", fmt.Errorf("解析 dts_master_addr 失败: %w", err)
	}
	u.Path = apiPath
	u.RawQuery = ""
	return u.String(), nil
}

// FetchTaskStatus HTTP GET http://{dts_master_addr}/api/v1/tasks/{task_name}/status
func FetchTaskStatus(dtsMasterAddr, taskName string, timeoutSec int) (*TaskStatusListResponse, error) {
	if timeoutSec <= 0 {
		timeoutSec = 30
	}
	u, err := buildMasterAPIURL(dtsMasterAddr, fmt.Sprintf("/api/v1/tasks/%s/status", url.PathEscape(taskName)))
	if err != nil {
		return nil, err
	}

	client := &http.Client{Timeout: time.Duration(timeoutSec) * time.Second}
	req, err := http.NewRequest(http.MethodGet, u, nil)
	if err != nil {
		return nil, fmt.Errorf("构造 status 请求失败: %w", err)
	}
	logger.Info("查询 DTS 任务状态: %s", req.URL.String())
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("查询任务状态失败: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("查询任务状态 HTTP %d", resp.StatusCode)
	}
	var out TaskStatusListResponse
	if err = json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, fmt.Errorf("解析任务状态 JSON 失败: %w", err)
	}
	return &out, nil
}

// statusSourceKey 取 status item 的 source 键（优先 source_name）。
func statusSourceKey(item TaskStatusItem) string {
	if item.SourceName != "" {
		return item.SourceName
	}
	return item.Name
}

// BuildLockMasterSnapshots 加锁后从 taskStatus 按 source 记录当时的 master 位点快照。
func BuildLockMasterSnapshots(items []TaskStatusItem) (map[string]BinlogCoord, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("任务状态为空，无法建立加锁位点快照")
	}
	out := make(map[string]BinlogCoord, len(items))
	for _, item := range items {
		src := statusSourceKey(item)
		if item.SyncStatus == nil {
			return nil, fmt.Errorf("source %s 缺少 sync_status，无法建立加锁位点快照", src)
		}
		coord, ok := ParseBinlogCoord(item.SyncStatus.MasterBinlog)
		if !ok {
			return nil, fmt.Errorf("source %s master_binlog 非法，无法建立加锁位点快照: %q", src, item.SyncStatus.MasterBinlog)
		}
		out[src] = coord
	}
	return out, nil
}

// CheckSnapshotCatchup 持锁复核：所有 source 须 SBM==0、syncer>=加锁 master 快照、无 blocking_ddls。
// 数据一致性由编排侧已完成的 checksum 兜底；实时 master 前进不影响判定。
// 对称约束：本轮 status 必须覆盖 snapshots 中每一个 source，禁止子集追平假成功。
func CheckSnapshotCatchup(items []TaskStatusItem, snapshots map[string]BinlogCoord) error {
	if len(items) == 0 {
		return fmt.Errorf("任务状态为空，无法复核追平")
	}
	if len(snapshots) == 0 {
		return fmt.Errorf("加锁位点快照为空，无法复核追平")
	}
	seen := make(map[string]struct{}, len(items))
	for _, item := range items {
		src := statusSourceKey(item)
		seen[src] = struct{}{}
		if item.ErrorMsg != "" {
			return fmt.Errorf("source %s 任务错误: %s", src, item.ErrorMsg)
		}
		if item.SyncStatus == nil {
			return fmt.Errorf("source %s 缺少 sync_status", src)
		}
		ss := item.SyncStatus
		if len(ss.BlockingDDLs) > 0 {
			return fmt.Errorf("source %s 存在 blocking_ddls: %v", src, ss.BlockingDDLs)
		}
		snap, ok := snapshots[src]
		if !ok {
			return fmt.Errorf("source %s 缺少加锁位点快照", src)
		}
		if !IsCaughtUpToSnapshot(ss.SyncerBinlog, snap, ss.SecondsBehindMaster) {
			return fmt.Errorf(
				"source %s 未追上加锁快照(需 SBM=0 且 syncer>=lock_master): sbm=%d lock_master=(%s, %d) syncer_binlog=%q live_master=%q",
				src, ss.SecondsBehindMaster, snap.File, snap.Position, ss.SyncerBinlog, ss.MasterBinlog,
			)
		}
	}
	for src := range snapshots {
		if _, ok := seen[src]; !ok {
			return fmt.Errorf("加锁快照含 source %s，但本轮 status 未返回该源，拒绝追平假成功", src)
		}
	}
	return nil
}

// BuildPositionOutput 从 status 列表构造输出位点。
func BuildPositionOutput(taskName string, items []TaskStatusItem) CutoverPositionOutput {
	out := CutoverPositionOutput{
		TaskName:  taskName,
		StoppedAt: time.Now().UTC().Format(time.RFC3339),
		Sources:   make([]SourcePositionSnapshot, 0, len(items)),
	}
	for _, item := range items {
		snap := SourcePositionSnapshot{SourceName: item.SourceName}
		if item.SyncStatus != nil {
			snap.MasterBinlog = item.SyncStatus.MasterBinlog
			snap.MasterBinlogGtid = item.SyncStatus.MasterBinlogGtid
			snap.SyncerBinlog = item.SyncStatus.SyncerBinlog
			snap.SyncerBinlogGtid = item.SyncStatus.SyncerBinlogGtid
			snap.SecondsBehind = item.SyncStatus.SecondsBehindMaster
		}
		out.Sources = append(out.Sources, snap)
	}
	return out
}
