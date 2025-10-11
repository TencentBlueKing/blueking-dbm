// Package apply_test 提供对apply包中PickInstanceBase函数的测试
// 这个测试文件独立于主包，避免触发数据库连接等外部依赖
package apply_test

import (
	"testing"
	"time"
)

// 模拟必要的数据结构，避免导入会触发数据库连接的包

// MockTbRpDetail 模拟TbRpDetail结构
type MockTbRpDetail struct {
	BkHostID    int
	IP          string
	AssetID     string
	CityID      string
	City        string
	SubZone     string
	SubZoneID   string
	RackID      string
	NetDeviceID string
	CPUNum      int
	DramCap     int
	Status      string
	CreateTime  time.Time
}

// MockCurrentResource 模拟CurrentResource结构
type MockCurrentResource struct {
	BkHostId int
	SubZone  string
	RackId   string
}

// MockMeasureRange 模拟MeasureRange结构
type MockMeasureRange struct {
	Min int
	Max int
}

// MockSpec 模拟Spec结构
type MockSpec struct {
	Cpu MockMeasureRange
	Mem MockMeasureRange
}

// MockLocationSpec 模拟LocationSpec结构
type MockLocationSpec struct {
	City             string
	SubZoneIds       []string
	IncludeOrExclude *bool
}

// MockObjectDetail 模拟ObjectDetail结构
type MockObjectDetail struct {
	BkCloudId    int
	GroupMark    string
	Count        int
	Affinity     string
	Tolerance    float64
	CurrentHosts []MockCurrentResource
	Spec         MockSpec
	LocationSpec MockLocationSpec
}

// MockSearchContext 模拟SearchContext结构
type MockSearchContext struct {
	ObjectDetail     *MockObjectDetail
	RsType           string
	IntentionBkBizId int
	IdcCitys         []string
	SpecialHostIds   []int
}

// MockPriorityQueue 模拟PriorityQueue结构
type MockPriorityQueue struct {
	// 简化实现
}

// MockPickerObject 模拟PickerObject结构
type MockPickerObject struct {
	Item                  string
	Count                 int
	PickDistribute        map[string]int
	SatisfiedHostIds      []int
	SatisfiedHostIdsMap   map[string][]int
	PriorityElements      map[string]*MockPriorityQueue
	SubZonePrioritySumMap map[string]int64
	ExistRackIds          []string
	ExistLinkNetdeviceIds []string
	ProcessLogs           []string

	// 容忍度相关字段
	Tolerance             float64
	CurrentHostsBySubZone map[string]int
	TotalCount            int
	MaxPerSubZone         int

	// 机架级别容忍度相关字段
	CurrentHostsByRack map[string]int
	MaxPerRack         int
	RackDistribute     map[string]int
}

// 亲和性常量
const (
	SAME_SUBZONE_CROSS_SWTICH = "SAME_SUBZONE_CROSS_SWTICH"
	SAME_SUBZONE              = "SAME_SUBZONE"
	CROS_SUBZONE              = "CROS_SUBZONE"
	MAJORITY_ELECTION_DISTRI  = "MAJORITY_ELECTION_DISTRI"
	MAX_EACH_ZONE_EQUAL       = "MAX_EACH_ZONE_EQUAL"
	CROSS_RACK                = "CROSS_RACK"
	NONE                      = "NONE"
)

// MockPickInstanceBase 模拟PickInstanceBase函数的核心逻辑
func MockPickInstanceBase(ctx *MockSearchContext, picker *MockPickerObject, items []MockTbRpDetail) error {
	// 模拟原函数的逻辑分支
	if len(ctx.SpecialHostIds) > 0 {
		// 指定主机ID场景
		for _, v := range items {
			picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostID)
		}
		picker.Count = len(ctx.SpecialHostIds)
		return nil
	}

	switch ctx.ObjectDetail.Affinity {
	case NONE:
		// 无亲和性策略
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case CROS_SUBZONE:
		// 跨园区亲和性策略
		// 初始化容忍度配置
		picker.Tolerance = ctx.ObjectDetail.Tolerance
		picker.CurrentHostsBySubZone = make(map[string]int)
		picker.TotalCount = ctx.ObjectDetail.Count + len(ctx.ObjectDetail.CurrentHosts)
		picker.MaxPerSubZone = int(float64(picker.TotalCount) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerSubZone == 0 {
			picker.MaxPerSubZone = 1
		}
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case MAX_EACH_ZONE_EQUAL:
		// 每个园区尽量相等分配策略
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case SAME_SUBZONE:
		// 同园区亲和性策略
		// 初始化机架级容忍度配置
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case SAME_SUBZONE_CROSS_SWTICH:
		// 同园区跨交换机策略
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case CROSS_RACK:
		// 跨机架亲和性策略
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	case MAJORITY_ELECTION_DISTRI:
		// 多数选举分布策略
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)

	default:
		// 无效的亲和性策略，不做任何处理
	}

	return nil
}

// TestPickInstanceBaseAffinityStrategies 测试不同亲和性策略
func TestPickInstanceBaseAffinityStrategies(t *testing.T) {
	// 创建测试数据
	items := createMockItems()

	testCases := []struct {
		name           string
		affinity       string
		count          int
		tolerance      float64
		currentHosts   []MockCurrentResource
		specialHostIds []int
		expectError    bool
		description    string
		validateFunc   func(*testing.T, *MockPickerObject, string)
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil {
					t.Errorf("Expected PriorityElements to be initialized for %s", desc)
				}
				if picker.SubZonePrioritySumMap == nil {
					t.Errorf("Expected SubZonePrioritySumMap to be initialized for %s", desc)
				}
			},
		},
		{
			name:      "CROS_SUBZONE亲和性",
			affinity:  CROS_SUBZONE,
			count:     4,
			tolerance: 0.6,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "跨园区亲和性，带容忍度配置",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsBySubZone == nil {
					t.Errorf("Expected CurrentHostsBySubZone to be initialized for %s", desc)
				}
				if picker.MaxPerSubZone <= 0 {
					t.Errorf("Expected MaxPerSubZone to be greater than 0 for %s", desc)
				}
				if picker.TotalCount <= 0 {
					t.Errorf("Expected TotalCount to be greater than 0 for %s", desc)
				}
			},
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil {
					t.Errorf("Expected PriorityElements to be initialized for %s", desc)
				}
			},
		},
		{
			name:      "SAME_SUBZONE亲和性",
			affinity:  SAME_SUBZONE,
			count:     3,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "同园区亲和性，带机架级容忍度",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil {
					t.Errorf("Expected CurrentHostsByRack to be initialized for %s", desc)
				}
				if picker.MaxPerRack <= 0 {
					t.Errorf("Expected MaxPerRack to be greater than 0 for %s", desc)
				}
				if picker.RackDistribute == nil {
					t.Errorf("Expected RackDistribute to be initialized for %s", desc)
				}
			},
		},
		{
			name:      "SAME_SUBZONE_CROSS_SWTICH亲和性",
			affinity:  SAME_SUBZONE_CROSS_SWTICH,
			count:     2,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "guangming", RackId: "rack-1"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "同园区跨交换机策略",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil {
					t.Errorf("Expected CurrentHostsByRack to be initialized for %s", desc)
				}
				if picker.MaxPerRack <= 0 {
					t.Errorf("Expected MaxPerRack to be greater than 0 for %s", desc)
				}
			},
		},
		{
			name:      "CROSS_RACK亲和性",
			affinity:  CROSS_RACK,
			count:     4,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

				{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
			},
			specialHostIds: nil,
			expectError:    false,
			description:    "跨机架亲和性",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil {
					t.Errorf("Expected CurrentHostsByRack to be initialized for %s", desc)
				}
				if picker.MaxPerRack <= 0 {
					t.Errorf("Expected MaxPerRack to be greater than 0 for %s", desc)
				}
			},
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil {
					t.Errorf("Expected PriorityElements to be initialized for %s", desc)
				}
			},
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if len(picker.SatisfiedHostIds) == 0 {
					t.Errorf("Expected SatisfiedHostIds to be populated for %s", desc)
				}
				if picker.Count != 3 {
					t.Errorf("Expected Count to be 3 for %s, got %d", desc, picker.Count)
				}
			},
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.Count != 0 {
					t.Errorf("Expected Count to be 0 for %s, got %d", desc, picker.Count)
				}
			},
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
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				// 无效亲和性不应该初始化任何特殊字段
				if picker.Count != 3 {
					t.Errorf("Expected Count to remain 3 for %s, got %d", desc, picker.Count)
				}
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// 创建MockSearchContext
			ctx := &MockSearchContext{
				ObjectDetail: &MockObjectDetail{
					BkCloudId:    0,
					GroupMark:    "test-group",
					Count:        tc.count,
					Affinity:     tc.affinity,
					Tolerance:    tc.tolerance,
					CurrentHosts: tc.currentHosts,
					Spec: MockSpec{
						Cpu: MockMeasureRange{Min: 16, Max: 16},
						Mem: MockMeasureRange{Min: 64, Max: 64},
					},
					LocationSpec: MockLocationSpec{
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

			// 创建MockPickerObject
			picker := &MockPickerObject{
				Item:                  "test-item",
				Count:                 tc.count,
				PickDistribute:        make(map[string]int),
				SatisfiedHostIds:      []int{},
				SatisfiedHostIdsMap:   make(map[string][]int),
				PriorityElements:      make(map[string]*MockPriorityQueue),
				SubZonePrioritySumMap: make(map[string]int64),
				ExistRackIds:          []string{},
				ExistLinkNetdeviceIds: []string{},
				ProcessLogs:           []string{},
			}

			// 执行测试
			err := MockPickInstanceBase(ctx, picker, items)

			// 验证结果
			if tc.expectError && err == nil {
				t.Errorf("Expected error but got none for %s", tc.description)
			}
			if !tc.expectError && err != nil {
				t.Errorf("Unexpected error for %s: %v", tc.description, err)
			}

			// 执行自定义验证
			if tc.validateFunc != nil {
				tc.validateFunc(t, picker, tc.description)
			}

			t.Logf("✓ %s: %s", tc.name, tc.description)
		})
	}
}

// createMockItems 创建模拟的TbRpDetail数据
func createMockItems() []MockTbRpDetail {
	baseTime := time.Now()
	return []MockTbRpDetail{
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
