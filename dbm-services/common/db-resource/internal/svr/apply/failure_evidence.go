/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package apply

import (
	"fmt"
	"strings"

	"dbm-services/common/db-resource/internal/model"
)

// 申请失败发生在匹配链路的哪一层。只描述层级，不表示根因。
const (
	// FailStagePickCheck SQL 预筛阶段候选总数不足
	FailStagePickCheck = "pick_check"
	// FailStageEmptyMountDisk 无挂载点磁盘的内存过滤阶段
	FailStageEmptyMountDisk = "empty_mount_disk"
	// FailStageAffinity 亲和性打散阶段未凑满申请数量
	FailStageAffinity = "affinity"
	// FailStageCAS 预选状态 CAS 抢占失败
	FailStageCAS = "cas"
)

// MatchStageCount 按 pickBase 顺序逐步叠加条件后的剩余台数。
// 只记录观测数字，不做归因：count 的变化依赖叠加顺序，单独一步下降不能当成根因。
type MatchStageCount struct {
	Name        string `json:"name"`
	Count       int64  `json:"count"`
	Requested   int    `json:"requested"`
	Description string `json:"description"`
}

// AffinitySnapshot 进入 picker 的候选机器分布快照
type AffinitySnapshot struct {
	AffinityType     string                    `json:"affinity_type"`
	AvailableCount   int                       `json:"available_count"`
	RequestCount     int                       `json:"request_count"`
	UniqueSubZones   int                       `json:"unique_subzones"`
	UniqueRacks      int                       `json:"unique_racks"`
	UniqueNetDevices int                       `json:"unique_net_devices"`
	BySubZone        map[string]int            `json:"by_subzone"`
	ByRack           map[string]int            `json:"by_rack"`
	ByNetDevice      map[string]int            `json:"by_net_device"`
	RacksBySubZone   map[string]map[string]int `json:"racks_by_subzone"`
}

// ApplyFailureEvidence 资源申请失败现场。作为观测数据交给分析智能体，不含根因结论。
type ApplyFailureEvidence struct {
	Stage          string            `json:"stage"`
	GroupMark      string            `json:"group_mark"`
	Affinity       string            `json:"affinity"`
	RequestCount   int               `json:"request_count"`
	Funnel         []MatchStageCount `json:"funnel,omitempty"`
	CandidateCount int               `json:"candidate_count,omitempty"`
	PickedCount    int               `json:"picked_count,omitempty"`
	MissingIps     []string          `json:"missing_ips,omitempty"`
	ProcessLogs    []string          `json:"process_logs,omitempty"`
	Distribution   *AffinitySnapshot `json:"distribution,omitempty"`
	Note           string            `json:"note,omitempty"`
}

// ResourceInsufficientError 携带失败现场的资源不足错误
type ResourceInsufficientError struct {
	Evidence ApplyFailureEvidence
	Message  string
	Err      error
}

// Error 返回给人看的失败说明
func (e *ResourceInsufficientError) Error() string {
	if e.Err != nil && e.Message == "" {
		return e.Err.Error()
	}
	return e.Message
}

// Unwrap 保留底层错误
func (e *ResourceInsufficientError) Unwrap() error {
	return e.Err
}

// NewResourceInsufficientError 构造带现场的资源不足错误
func NewResourceInsufficientError(evidence ApplyFailureEvidence, err error, message string) error {
	return &ResourceInsufficientError{
		Evidence: evidence,
		Message:  message,
		Err:      err,
	}
}

// newPreselectFailedError 机器已挑出但预选状态更新失败，记录 CAS 层现场
func newPreselectFailedError(detail *ObjectDetail, picker *PickerObject, updateErr error) error {
	return NewResourceInsufficientError(ApplyFailureEvidence{
		Stage:        FailStageCAS,
		GroupMark:    detail.GroupMark,
		Affinity:     detail.Affinity,
		RequestCount: detail.Count,
		PickedCount:  len(picker.SatisfiedHostIds),
		Note:         "已挑选到机器,但预选状态更新失败,通常是并发申请抢占同一批资源",
	}, updateErr, fmt.Sprintf("update %s Picker Out Satisfied Instance Status to Preselected Failed:%v",
		detail.GroupMark, updateErr.Error()))
}

// FormatFunnel 把漏斗渲染成逐步剩余台数，不输出任何原因推断
func FormatFunnel(funnel []MatchStageCount) string {
	if len(funnel) == 0 {
		return ""
	}
	parts := make([]string, 0, len(funnel))
	for _, stage := range funnel {
		parts = append(parts, fmt.Sprintf("%s=%d", stage.Name, stage.Count))
	}
	return fmt.Sprintf("按申请 SQL 顺序逐步叠加条件后的剩余台数(申请%d台): %s",
		funnel[0].Requested, strings.Join(parts, ", "))
}

// BuildAffinitySnapshot 统计进入 picker 的候选机器在园区/机架/交换机上的分布
func BuildAffinitySnapshot(affinity string, requestCount int, items []model.TbRpDetail) *AffinitySnapshot {
	snapshot := &AffinitySnapshot{
		AffinityType:   affinity,
		AvailableCount: len(items),
		RequestCount:   requestCount,
		BySubZone:      make(map[string]int),
		ByRack:         make(map[string]int),
		ByNetDevice:    make(map[string]int),
		RacksBySubZone: make(map[string]map[string]int),
	}
	for _, item := range items {
		if item.SubZoneID != "" {
			snapshot.BySubZone[item.SubZoneID]++
		}
		if item.RackID != "" {
			snapshot.ByRack[item.RackID]++
		}
		if item.NetDeviceID != "" {
			snapshot.ByNetDevice[item.NetDeviceID]++
		}
		if item.SubZoneID != "" && item.RackID != "" {
			if _, ok := snapshot.RacksBySubZone[item.SubZoneID]; !ok {
				snapshot.RacksBySubZone[item.SubZoneID] = make(map[string]int)
			}
			snapshot.RacksBySubZone[item.SubZoneID][item.RackID]++
		}
	}
	snapshot.UniqueSubZones = len(snapshot.BySubZone)
	snapshot.UniqueRacks = len(snapshot.ByRack)
	snapshot.UniqueNetDevices = len(snapshot.ByNetDevice)
	return snapshot
}
