/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"strings"
	"testing"

	"dbm-services/common/db-resource/internal/svr/apply"
)

func sceneApplyParams() *apply.RequestInputParam {
	return &apply.RequestInputParam{
		ResourceType: "mysql",
		Details: []apply.ObjectDetail{
			{
				GroupMark: "master_group",
				Count:     3,
				Affinity:  apply.CROSS_SUBZONE_STRONG,
			},
		},
	}
}

// TestBuildUserMessageWithSceneNilEvidence 没有现场时行为与原来一致
func TestBuildUserMessageWithSceneNilEvidence(t *testing.T) {
	params := sceneApplyParams()
	if got := BuildUserMessageWithScene(params, nil); got != BuildUserMessage(params) {
		t.Error("现场为空时应退回原有 BuildUserMessage")
	}
}

// TestBuildUserMessageWithSceneIsObservationNotConclusion
// 现场必须以观测数据的口吻注入，不能宣称根因已定
func TestBuildUserMessageWithSceneIsObservationNotConclusion(t *testing.T) {
	evidence := &apply.ApplyFailureEvidence{
		Stage:          apply.FailStageAffinity,
		GroupMark:      "master_group",
		Affinity:       apply.CROSS_SUBZONE_STRONG,
		RequestCount:   3,
		CandidateCount: 10,
		PickedCount:    2,
		Funnel: []apply.MatchStageCount{
			{Name: "base", Count: 100, Requested: 3, Description: "基础条件"},
			{Name: "spec", Count: 10, Requested: 3, Description: "叠加规格后"},
		},
		ProcessLogs: []string{"园区268不满足跨园区要求"},
		Distribution: &apply.AffinitySnapshot{
			AffinityType:     apply.CROSS_SUBZONE_STRONG,
			AvailableCount:   10,
			RequestCount:     3,
			UniqueSubZones:   1,
			UniqueRacks:      2,
			UniqueNetDevices: 2,
			BySubZone:        map[string]int{"268": 10},
			ByRack:           map[string]int{"rack-a": 6, "rack-b": 4},
			ByNetDevice:      map[string]int{"sw-1": 6, "sw-2": 4},
			RacksBySubZone:   map[string]map[string]int{"268": {"rack-a": 6, "rack-b": 4}},
		},
		Note: "process_logs 为分配过程日志,不是结论",
	}

	message := BuildUserMessageWithScene(sceneApplyParams(), evidence)

	// 必须表明是观测数据，且明确要求模型自己判断原因
	mustContain := []string{
		"申请失败现场（观测数据，不是结论）",
		"原因需要你自己分析判断",
		apply.FailStageAffinity,
		"master_group",
		"base: 100 台",
		"spec: 10 台",
		"进入分配阶段的候选台数: 10",
		"实际分配到的台数: 2",
		"园区268不满足跨园区要求",
		"分配过程日志（过程记录，不是结论）",
		"不要把某一步 count 下降直接当成唯一根本原因",
		"叠加顺序与真实申请 SQL 完全一致",
	}
	for _, want := range mustContain {
		if !strings.Contains(message, want) {
			t.Errorf("用户消息缺少内容: %s", want)
		}
	}

	// 不能走「原因已确定」的口径
	mustNotContain := []string{
		"已确定的失败原因",
		"你不需要重新分析",
		"推测的原因可能是",
	}
	for _, forbidden := range mustNotContain {
		if strings.Contains(message, forbidden) {
			t.Errorf("用户消息不应包含结论式表述: %s", forbidden)
		}
	}
}

// TestBuildUserMessageWithSceneMissingIps 指定 IP 场景没有漏斗，只报缺失 IP
func TestBuildUserMessageWithSceneMissingIps(t *testing.T) {
	evidence := &apply.ApplyFailureEvidence{
		Stage:        apply.FailStagePickCheck,
		GroupMark:    "master_group",
		RequestCount: 2,
		MissingIps:   []string{"127.0.0.2", "127.0.0.3"},
		Note:         "指定 bk_host_id 申请,未经过按条件逐步筛选,无漏斗数据",
	}

	message := BuildUserMessageWithScene(sceneApplyParams(), evidence)

	if !strings.Contains(message, "127.0.0.2") || !strings.Contains(message, "127.0.0.3") {
		t.Error("用户消息应列出不可用的指定 IP")
	}
	if strings.Contains(message, "逐步叠加匹配条件后的剩余台数") {
		t.Error("没有漏斗数据时不应输出漏斗小节")
	}
	if !strings.Contains(message, "无漏斗数据") {
		t.Error("应说明该场景没有漏斗数据")
	}
}

// TestDescribeFailStage 每个失败层级都有可读说明
func TestDescribeFailStage(t *testing.T) {
	stages := []string{
		apply.FailStagePickCheck,
		apply.FailStageEmptyMountDisk,
		apply.FailStageAffinity,
		apply.FailStageCAS,
	}
	for _, stage := range stages {
		desc := describeFailStage(stage)
		if desc == "" || desc == unknownFailStageDesc {
			t.Errorf("失败层级 %s 缺少说明", stage)
		}
		// 说明只讲发生在哪一层，不能写成根因
		if strings.Contains(desc, "根本原因") || strings.Contains(desc, "根因") {
			t.Errorf("失败层级 %s 的说明不应表述为根因: %s", stage, desc)
		}
	}
	if describeFailStage("something_else") != unknownFailStageDesc {
		t.Error("未知层级应返回未知阶段")
	}
}
