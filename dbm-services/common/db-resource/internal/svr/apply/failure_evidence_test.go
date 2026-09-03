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
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"dbm-services/common/db-resource/internal/model"
)

// TestMatchStepsOrder 漏斗的叠加顺序必须就是 pickBase 的叠加顺序。
// pickBase 与 CollectMatchFunnel 都遍历 matchSteps，这里锁定它的顺序，防止悄悄漂移。
func TestMatchStepsOrder(t *testing.T) {
	baseOrder := []string{"base", "biz", "rsType", "osType", "osName", "labels", "location", "storage", "spec"}

	cases := []struct {
		name     string
		affinity string
		expected []string
	}{
		{
			name:     "无亲和性要求",
			affinity: NONE,
			expected: baseOrder,
		},
		{
			name:     "同园区跨交换机追加网卡id非空",
			affinity: SAME_SUBZONE_CROSS_SWTICH,
			expected: append(append([]string{}, baseOrder...), "netDevice"),
		},
		{
			name:     "跨园区强制追加机架id非空",
			affinity: CROSS_SUBZONE_STRONG,
			expected: append(append([]string{}, baseOrder...), "rackId"),
		},
		{
			name:     "跨机架追加机架id非空",
			affinity: CROSS_RACK,
			expected: append(append([]string{}, baseOrder...), "rackId"),
		},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			ctx := &SearchContext{
				ObjectDetail: &ObjectDetail{
					BkCloudId: 0,
					GroupMark: "test_group",
					Count:     3,
					Affinity:  c.affinity,
				},
			}
			steps := ctx.matchSteps()
			got := make([]string, 0, len(steps))
			for _, step := range steps {
				got = append(got, step.name)
				if step.fn == nil {
					t.Errorf("步骤 %s 没有匹配函数", step.name)
				}
				if step.desc == "" {
					t.Errorf("步骤 %s 缺少描述", step.name)
				}
			}
			if strings.Join(got, ",") != strings.Join(c.expected, ",") {
				t.Errorf("匹配步骤顺序不符\n期望: %v\n实际: %v", c.expected, got)
			}
		})
	}
}

// TestMatchStageCountHasNoAttribution 漏斗只承载观测数字，不能出现归因字段
func TestMatchStageCountHasNoAttribution(t *testing.T) {
	raw, err := json.Marshal(MatchStageCount{Name: "spec", Count: 1, Requested: 3, Description: "叠加规格后"})
	if err != nil {
		t.Fatalf("序列化失败: %v", err)
	}
	var fields map[string]interface{}
	if err = json.Unmarshal(raw, &fields); err != nil {
		t.Fatalf("反序列化失败: %v", err)
	}
	for _, forbidden := range []string{"bottleneck", "reason", "root_cause", "is_bottleneck"} {
		if _, ok := fields[forbidden]; ok {
			t.Errorf("漏斗步骤不应包含归因字段 %s", forbidden)
		}
	}
}

// TestResourceInsufficientErrorUnwrap errors.As 能取出现场，Unwrap 保留底层错误
func TestResourceInsufficientErrorUnwrap(t *testing.T) {
	underlying := errors.New("底层错误")
	evidence := ApplyFailureEvidence{
		Stage:        FailStageAffinity,
		GroupMark:    "master_group",
		Affinity:     CROSS_SUBZONE_STRONG,
		RequestCount: 3,
		Funnel: []MatchStageCount{
			{Name: "base", Count: 100, Requested: 3, Description: "基础条件"},
			{Name: "spec", Count: 5, Requested: 3, Description: "叠加规格后"},
		},
	}
	err := NewResourceInsufficientError(evidence, underlying, "资源不足了")

	// 包一层，模拟上层继续 wrap 的情况
	wrapped := fmt.Errorf("apply failed: %w", err)

	var target *ResourceInsufficientError
	if !errors.As(wrapped, &target) {
		t.Fatal("errors.As 没能取出 ResourceInsufficientError")
	}
	if target.Evidence.Stage != FailStageAffinity {
		t.Errorf("stage 期望 %s, 实际 %s", FailStageAffinity, target.Evidence.Stage)
	}
	if target.Evidence.GroupMark != "master_group" {
		t.Errorf("group_mark 期望 master_group, 实际 %s", target.Evidence.GroupMark)
	}
	if len(target.Evidence.Funnel) != 2 {
		t.Errorf("漏斗步骤数期望 2, 实际 %d", len(target.Evidence.Funnel))
	}
	if !errors.Is(wrapped, underlying) {
		t.Error("Unwrap 应保留底层错误")
	}
	if target.Error() != "资源不足了" {
		t.Errorf("Error() 期望返回给人看的说明, 实际 %s", target.Error())
	}
}

// TestFormatFunnelNoAttribution HTTP 文案只跟剩余台数，不写「推测的原因可能是」
func TestFormatFunnelNoAttribution(t *testing.T) {
	funnel := []MatchStageCount{
		{Name: "base", Count: 100, Requested: 3, Description: "基础条件"},
		{Name: "location", Count: 20, Requested: 3, Description: "叠加地域后"},
		{Name: "spec", Count: 1, Requested: 3, Description: "叠加规格后"},
	}
	text := FormatFunnel(funnel)

	for _, want := range []string{"base=100", "location=20", "spec=1", "申请3台"} {
		if !strings.Contains(text, want) {
			t.Errorf("文案应包含 %s, 实际: %s", want, text)
		}
	}
	for _, forbidden := range []string{"推测的原因可能是", "没有匹配到资源", "根本原因", "卡在"} {
		if strings.Contains(text, forbidden) {
			t.Errorf("文案不应包含归因表述 %s, 实际: %s", forbidden, text)
		}
	}
	if FormatFunnel(nil) != "" {
		t.Error("空漏斗应返回空字符串")
	}
}

// TestBuildAffinitySnapshot 候选分布快照按园区/机架/交换机聚合
func TestBuildAffinitySnapshot(t *testing.T) {
	items := []model.TbRpDetail{
		{SubZoneID: "268", RackID: "rack-a", NetDeviceID: "sw-1"},
		{SubZoneID: "268", RackID: "rack-a", NetDeviceID: "sw-1"},
		{SubZoneID: "268", RackID: "rack-b", NetDeviceID: "sw-2"},
		{SubZoneID: "1109", RackID: "rack-c", NetDeviceID: "sw-3"},
		// 机架信息缺失的机器不进入机架统计
		{SubZoneID: "1109"},
	}
	snapshot := BuildAffinitySnapshot(CROSS_SUBZONE_STRONG, 4, items)

	if snapshot.AvailableCount != 5 {
		t.Errorf("候选台数期望 5, 实际 %d", snapshot.AvailableCount)
	}
	if snapshot.RequestCount != 4 {
		t.Errorf("申请台数期望 4, 实际 %d", snapshot.RequestCount)
	}
	if snapshot.UniqueSubZones != 2 {
		t.Errorf("园区数期望 2, 实际 %d", snapshot.UniqueSubZones)
	}
	if snapshot.UniqueRacks != 3 {
		t.Errorf("机架数期望 3, 实际 %d", snapshot.UniqueRacks)
	}
	if snapshot.UniqueNetDevices != 3 {
		t.Errorf("交换机数期望 3, 实际 %d", snapshot.UniqueNetDevices)
	}
	if snapshot.BySubZone["268"] != 3 {
		t.Errorf("园区268 期望 3 台, 实际 %d", snapshot.BySubZone["268"])
	}
	if len(snapshot.RacksBySubZone["268"]) != 2 {
		t.Errorf("园区268 期望 2 个机架, 实际 %d", len(snapshot.RacksBySubZone["268"]))
	}
	if snapshot.RacksBySubZone["268"]["rack-a"] != 2 {
		t.Errorf("园区268 rack-a 期望 2 台, 实际 %d", snapshot.RacksBySubZone["268"]["rack-a"])
	}
	if _, ok := snapshot.RacksBySubZone["1109"]["rack-c"]; !ok {
		t.Error("园区1109 应统计到 rack-c")
	}
}
