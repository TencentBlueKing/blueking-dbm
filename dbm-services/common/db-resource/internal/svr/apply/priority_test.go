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
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// mockHost 构造最小可用的资源记录（唯一 BkHostID）
func mockHost(id int, subZone, rack, netDev, deviceClass string) model.TbRpDetail {
	return model.TbRpDetail{
		BkHostID:      id,
		IP:            fmt.Sprintf("10.0.%d.%d", id/100, id%100),
		SubZone:       subZone,
		SubZoneID:     subZone + "_id",
		RackID:        rack,
		NetDeviceID:   netDev,
		CPUNum:        8,
		DramCap:       16384,
		DeviceClass:   deviceClass,
		StorageDevice: []byte(`{"/data":{"size":100,"disk_id":"d1","disk_type":"SSD","file_type":"ext4"}}`),
		CreateTime:    time.Now().Add(-24 * time.Hour),
		Status:        "Ready",
		City:          "sz",
		CityID:        "sz",
	}
}

// TestPriorityQueueOrder 验证队列顺序为“数值越大优先级越高”
func TestPriorityQueueOrder(t *testing.T) {
	pq := NewPriorityQueue()
	_ = pq.Push(&Item{Key: "a", Priority: 10})
	_ = pq.Push(&Item{Key: "b", Priority: 5})
	_ = pq.Push(&Item{Key: "c", Priority: 20})

	i1, _ := pq.Pop()
	i2, _ := pq.Pop()
	i3, _ := pq.Pop()

	if i1.Key != "c" || i2.Key != "a" || i3.Key != "b" {
		t.Fatalf("优先队列弹出顺序不符合预期: got %v,%v,%v", i1.Key, i2.Key, i3.Key)
	}
}

// TestAnalysisResourcePriority_NoDuplicate 验证无重复数据时能正常分析与入队
func TestAnalysisResourcePriority_NoDuplicate(t *testing.T) {
	// 构造两园区资源，各3台，主机ID唯一
	var items []model.TbRpDetail
	for i := 1; i <= 3; i++ {
		items = append(items, mockHost(100+i, "zoneA", "rackA1", "netA", "SA2.SMALL4"))
	}
	for i := 1; i <= 3; i++ {
		items = append(items, mockHost(200+i, "zoneB", "rackB1", "netB", "SA2.SMALL4"))
	}

	ctx := &SearchContext{
		IntentionBkBizId: 0,
		RsType:           "",
		ObjectDetail: &ObjectDetail{
			Affinity:  CROS_SUBZONE,
			Tolerance: 0.3,
			Spec:      meta.Spec{Cpu: meta.MeasureRange{Min: 1, Max: 16}},
		},
	}

	result, sumMap, err := ctx.AnalysisResourcePriority(items, false)
	if err != nil {
		t.Fatalf("AnalysisResourcePriority 失败: %v", err)
	}

	if len(result) != 2 {
		t.Fatalf("期望2个园区队列，实际=%d", len(result))
	}
	if _, ok := result["zoneA"]; !ok {
		t.Fatalf("缺少 zoneA 队列")
	}
	if _, ok := result["zoneB"]; !ok {
		t.Fatalf("缺少 zoneB 队列")
	}
	if result["zoneA"].Len() != 3 || result["zoneB"].Len() != 3 {
		t.Fatalf("每个园区应各3台，实际: zoneA=%d zoneB=%d", result["zoneA"].Len(), result["zoneB"].Len())
	}
	if len(sumMap) != 2 {
		t.Fatalf("期望2个园区优先级合计，实际=%d", len(sumMap))
	}
}
