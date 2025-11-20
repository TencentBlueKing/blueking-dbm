package apply

import (
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// TestPickInstanceBaseLogic 测试PickInstanceBase函数的逻辑
// 这个测试专注于验证不同亲和性策略的分支逻辑，不依赖外部资源
func TestPickInstanceBaseLogic(t *testing.T) {
	// 创建测试数据
	items := createMockItems()

	testCases := []struct {
		name           string
		affinity       string
		count          int
		tolerance      float64
		currentHosts   []CurrentResource
		specialHostIds []int
		expectError    bool
		description    string
	}{
		{
			name:           "NONE亲和性",
			affinity:       NONE,
			count:          3,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			expectError:    false,
			description:    "无亲和性策略，随机选择",
		},
		{
			name:      "CROS_SUBZONE亲和性",
			affinity:  CROS_SUBZONE,
			count:     4,
			tolerance: 0.6,
			currentHosts: []CurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "跨园区亲和性，带容忍度配置",
		},
		{
			name:           "MAX_EACH_ZONE_EQUAL亲和性",
			affinity:       MAX_EACH_ZONE_EQUAL,
			count:          6,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			expectError:    false,
			description:    "每个园区尽量相等分配",
		},
		{
			name:      "SAME_SUBZONE亲和性",
			affinity:  SAME_SUBZONE,
			count:     3,
			tolerance: 0.5,
			currentHosts: []CurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "同园区亲和性，带机架级容忍度",
		},
		{
			name:      "SAME_SUBZONE_CROSS_SWTICH亲和性",
			affinity:  SAME_SUBZONE_CROSS_SWTICH,
			count:     2,
			tolerance: 0.5,
			currentHosts: []CurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-1"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "同园区跨交换机策略",
		},
		{
			name:      "CROSS_RACK亲和性",
			affinity:  CROSS_RACK,
			count:     4,
			tolerance: 0.5,
			currentHosts: []CurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "跨机架亲和性",
		},
		{
			name:           "MAJORITY_ELECTION_DISTRI亲和性",
			affinity:       MAJORITY_ELECTION_DISTRI,
			count:          5,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			expectError:    false,
			description:    "多数选举分布策略",
		},
		{
			name:           "指定主机ID场景",
			affinity:       NONE,
			count:          3,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: []int{1001, 1002, 2001},
			expectError:    false,
			description:    "指定特定主机ID",
		},
		{
			name:           "零数量场景",
			affinity:       NONE,
			count:          0,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			expectError:    false,
			description:    "申请0台机器",
		},
		{
			name:           "无效亲和性",
			affinity:       "INVALID_AFFINITY",
			count:          3,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			expectError:    false,
			description:    "无效的亲和性策略",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// 创建SearchContext
			ctx := &SearchContext{
				ObjectDetail: &ObjectDetail{
					BkCloudId:    0,
					GroupMark:    "test-group",
					Count:        tc.count,
					Affinity:     tc.affinity,
					Tolerance:    tc.tolerance,
					CurrentHosts: tc.currentHosts,
					Spec: meta.Spec{
						Cpu: meta.MeasureRange{Min: 16, Max: 16},
						Mem: meta.MeasureRange{Min: 64, Max: 64},
					},
					LocationSpec: meta.LocationSpec{
						City:             "深圳",
						SubZoneIds:       []string{},
						IncludeOrExclude: nil,
					},
				},
				RsType:           "mysql",
				IntentionBkBizId: 1001,
				IdcCitys:         []string{"city-1"},
				SpecialHostIds:   tc.specialHostIds,
			}

			// 创建PickerObject
			picker := &PickerObject{
				Item:                  "test-item",
				Count:                 tc.count,
				PickDistribute:        make(map[string]int),
				SatisfiedHostIds:      []int{},
				SatisfiedHostIdsMap:   make(map[subZone][]int),
				PriorityElements:      make(map[subZone]*PriorityQueue),
				SubZonePrioritySumMap: make(map[subZone]int64),
				ExistRackIds:          []string{},
				ExistLinkNetdeviceIds: []string{},
				ProcessLogs:           []string{},
			}

			// 执行测试
			err := ctx.PickInstanceBase(picker, items)

			// 验证结果
			if tc.expectError && err == nil {
				t.Errorf("Expected error but got none for %s", tc.description)
			}
			if !tc.expectError && err != nil {
				t.Errorf("Unexpected error for %s: %v", tc.description, err)
			}

			// 验证基本属性
			if picker.Count != tc.count {
				t.Errorf("Expected count %d, got %d for %s", tc.count, picker.Count, tc.description)
			}

			// 对于指定主机ID的场景，验证主机ID是否正确设置
			if len(tc.specialHostIds) > 0 {
				t.Logf("picker.SatisfiedHostIds: %v\n", picker.SatisfiedHostIds)
				t.Logf("tc.specialHostIds: %v\n", tc.specialHostIds)
				if len(picker.SatisfiedHostIds) != len(tc.specialHostIds) {
					t.Errorf("Expected %d satisfied host IDs, got %d for %s",
						len(tc.specialHostIds), len(picker.SatisfiedHostIds), tc.description)
				}
			}

			t.Logf("✓ %s: %s", tc.name, tc.description)
		})
	}
}

// createMockItems 创建模拟的TbRpDetail数据
func createMockItems() []model.TbRpDetail {
	baseTime := time.Now()
	return []model.TbRpDetail{
		{
			BkHostID:    1001,
			IP:          "127.0.0.1",
			AssetID:     "asset-001",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "光明",
			SubZoneID:   "guangming",
			RackID:      "rack-1",
			NetDeviceID: "switch-1",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    1002,
			IP:          "127.0.0.2",
			AssetID:     "asset-002",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "光明",
			SubZoneID:   "guangming",
			RackID:      "rack-1",
			NetDeviceID: "switch-1",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    1003,
			IP:          "127.0.0.3",
			AssetID:     "asset-003",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "光明",
			SubZoneID:   "guangming",
			RackID:      "rack-2",
			NetDeviceID: "switch-2",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    1004,
			IP:          "127.0.0.4",
			AssetID:     "asset-004",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "光明",
			SubZoneID:   "guangming",
			RackID:      "rack-2",
			NetDeviceID: "switch-2",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    2001,
			IP:          "127.0.0.5",
			AssetID:     "asset-005",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "南山",
			SubZoneID:   "nanshan",
			RackID:      "rack-3",
			NetDeviceID: "switch-3",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    2002,
			IP:          "127.0.0.6",
			AssetID:     "asset-006",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "南山",
			SubZoneID:   "nanshan",
			RackID:      "rack-3",
			NetDeviceID: "switch-3",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    2003,
			IP:          "127.0.0.7",
			AssetID:     "asset-007",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "南山",
			SubZoneID:   "nanshan",
			RackID:      "rack-4",
			NetDeviceID: "switch-4",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    2004,
			IP:          "127.0.0.8",
			AssetID:     "asset-008",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "南山",
			SubZoneID:   "nanshan",
			RackID:      "rack-4",
			NetDeviceID: "switch-4",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    3001,
			IP:          "127.0.0.9",
			AssetID:     "asset-009",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "福田",
			SubZoneID:   "futian",
			RackID:      "rack-5",
			NetDeviceID: "switch-5",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
		{
			BkHostID:    3002,
			IP:          "127.0.0.10",
			AssetID:     "asset-010",
			CityID:      "city-1",
			City:        "深圳",
			SubZone:     "福田",
			SubZoneID:   "futian",
			RackID:      "rack-5",
			NetDeviceID: "switch-5",
			CPUNum:      16,
			DramCap:     64,
			Status:      "Unused",
			CreateTime:  baseTime,
		},
	}
}
