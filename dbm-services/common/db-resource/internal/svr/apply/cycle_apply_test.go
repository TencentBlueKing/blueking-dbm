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
	"testing"

	"dbm-services/common/db-resource/internal/svr/meta"
)

// TestCycleApply_PrintSummary 构造 CycleApply 的集成测试并输出 pickers summary
// 说明：
// - 为避免触发全局均衡（需要多组且容忍度>=0），此处设置 Tolerance=-1，走顺序分配路径
// - 使用 CROS_SUBZONE 亲和性以便输出按园区的分布（PickDistribute）
// - 测试结束后回滚资源状态到 Unused，避免污染环境
func TestCycleApply_PrintSummary(t *testing.T) {
	param := RequestInputParam{
		ResourceType: "MySQL",
		ForbizId:     0,
		Details: []ObjectDetail{
			{
				GroupMark: "group-1",
				Count:     2,
				Affinity:  CROS_SUBZONE,
				Tolerance: -1, // 禁用本组容忍度以避免全局均衡路径
				LocationSpec: meta.LocationSpec{
					City: "", // 不限制城市，尽量提高命中率
				},
			},
			{
				GroupMark: "group-2",
				Count:     2,
				Affinity:  CROS_SUBZONE,
				Tolerance: -1,
				LocationSpec: meta.LocationSpec{
					City: "",
				},
			},
		},
	}

	pickers, err := CycleApply(param)
	if err != nil {
		t.Fatalf("CycleApply 失败: %v", err)
	}
	// 测试结束后回滚状态
	defer RollBackAllInstanceUnused(pickers)

	// 打印每个分组的 summary（按园区分布与已选主机列表）
	t.Log("=== CycleApply 结果 Summary ===")
	for _, p := range pickers {
		t.Logf("组 %s: 申请=%d, 实际分配=%d", p.Item, p.Count, len(p.SatisfiedHostIds))

		// 打印各园区分布（PickDistribute 在跨园区策略下按 subZone 统计）
		if len(p.PickDistribute) == 0 {
			t.Log("  无园区分布（可能为随机或未命中分布统计场景）")
		} else {
			for subZone, cnt := range p.PickDistribute {
				t.Logf("  园区 %s: 新分配=%d", subZone, cnt)
			}
		}

		// 打印已分配主机ID
		if len(p.SatisfiedHostIds) > 0 {
			t.Logf("  主机列表: %v", p.SatisfiedHostIds)
		}
	}
}
