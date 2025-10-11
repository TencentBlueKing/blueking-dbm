// Package affinitytest provides standalone unit tests for affinity strategies
// This package intentionally avoids importing the apply package to prevent DB init side-effects
package affinitytest

import (
	"testing"
	"time"
)

// MockTbRpDetail simulates TbRpDetail
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

// MockCurrentResource simulates CurrentResource
type MockCurrentResource struct {
	BkHostId int
	SubZone  string
	RackId   string
}

// MockMeasureRange simulates MeasureRange
type MockMeasureRange struct {
	Min int
	Max int
}

// MockSpec simulates Spec
type MockSpec struct {
	Cpu MockMeasureRange
	Mem MockMeasureRange
}

// MockLocationSpec simulates LocationSpec
type MockLocationSpec struct {
	City             string
	SubZoneIds       []string
	IncludeOrExclude *bool
}

// MockObjectDetail simulates ObjectDetail
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

// MockSearchContext simulates SearchContext
type MockSearchContext struct {
	ObjectDetail     *MockObjectDetail
	RsType           string
	IntentionBkBizId int
	IdcCitys         []string
	SpecialHostIds   []int
}

// MockPriorityQueue simulates PriorityQueue (simplified)
type MockPriorityQueue struct{}

// MockPickerObject simulates PickerObject
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

	// tolerance per sub-zone
	Tolerance             float64
	CurrentHostsBySubZone map[string]int
	TotalCount            int
	MaxPerSubZone         int

	// rack-level tolerance
	CurrentHostsByRack map[string]int
	MaxPerRack         int
	RackDistribute     map[string]int
}

// affinity constants
const (
	SAME_SUBZONE_CROSS_SWTICH = "SAME_SUBZONE_CROSS_SWTICH"
	SAME_SUBZONE              = "SAME_SUBZONE"
	CROS_SUBZONE              = "CROS_SUBZONE"
	MAJORITY_ELECTION_DISTRI  = "MAJORITY_ELECTION_DISTRI"
	MAX_EACH_ZONE_EQUAL       = "MAX_EACH_ZONE_EQUAL"
	CROSS_RACK                = "CROSS_RACK"
	NONE                      = "NONE"
)

// MockPickInstanceBase simulates core branching of PickInstanceBase
func MockPickInstanceBase(ctx *MockSearchContext, picker *MockPickerObject, items []MockTbRpDetail) error {
	if len(ctx.SpecialHostIds) > 0 {
		for _, v := range items {
			picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostID)
		}
		picker.Count = len(ctx.SpecialHostIds)
		return nil
	}

	switch ctx.ObjectDetail.Affinity {
	case NONE:
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	case CROS_SUBZONE:
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
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	case SAME_SUBZONE:
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	case SAME_SUBZONE_CROSS_SWTICH:
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	case CROSS_RACK:
		picker.CurrentHostsByRack = make(map[string]int)
		picker.MaxPerRack = int(float64(ctx.ObjectDetail.Count+len(ctx.ObjectDetail.CurrentHosts)) * ctx.ObjectDetail.Tolerance)
		if picker.MaxPerRack == 0 {
			picker.MaxPerRack = 1
		}
		picker.RackDistribute = make(map[string]int)
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	case MAJORITY_ELECTION_DISTRI:
		picker.PriorityElements = make(map[string]*MockPriorityQueue)
		picker.SubZonePrioritySumMap = make(map[string]int64)
	}
	return nil
}

// TestPickInstanceBaseAffinityStrategies tests different affinity strategies
func TestPickInstanceBaseAffinityStrategies(t *testing.T) {
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
			name:           "NONE",
			affinity:       NONE,
			count:          3,
			tolerance:      0,
			currentHosts:   nil,
			specialHostIds: nil,
			description:    "no affinity",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil || picker.SubZonePrioritySumMap == nil {
					t.Errorf("expected maps initialized: %s", desc)
				}
			},
		},
		{
			name:      "CROS_SUBZONE",
			affinity:  CROS_SUBZONE,
			count:     4,
			tolerance: 0.6,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "subzone-1", RackId: "rack-1"},
				{BkHostId: 9002, SubZone: "subzone-1", RackId: "rack-2"},
			},
			description: "cross subzone with tolerance",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsBySubZone == nil || picker.MaxPerSubZone <= 0 || picker.TotalCount <= 0 {
					t.Errorf("expected subzone tolerance initialized: %s", desc)
				}
			},
		},
		{
			name:        "MAX_EACH_ZONE_EQUAL",
			affinity:    MAX_EACH_ZONE_EQUAL,
			count:       6,
			description: "equal per zone",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil {
					t.Errorf("expected PriorityElements: %s", desc)
				}
			},
		},
		{
			name:      "SAME_SUBZONE",
			affinity:  SAME_SUBZONE,
			count:     3,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "subzone-1", RackId: "rack-1"},
				{BkHostId: 9002, SubZone: "subzone-1", RackId: "rack-2"},
			},
			description: "same subzone rack-level",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil || picker.MaxPerRack <= 0 || picker.RackDistribute == nil {
					t.Errorf("expected rack tolerance initialized: %s", desc)
				}
			},
		},
		{
			name:      "SAME_SUBZONE_CROSS_SWTICH",
			affinity:  SAME_SUBZONE_CROSS_SWTICH,
			count:     2,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "subzone-1", RackId: "rack-1"},
				{BkHostId: 9002, SubZone: "subzone-1", RackId: "rack-1"},
			},
			description: "same subzone cross switch",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil || picker.MaxPerRack <= 0 {
					t.Errorf("expected rack tolerance initialized: %s", desc)
				}
			},
		},
		{
			name:      "CROSS_RACK",
			affinity:  CROSS_RACK,
			count:     4,
			tolerance: 0.5,
			currentHosts: []MockCurrentResource{
				{BkHostId: 9001, SubZone: "subzone-1", RackId: "rack-1"},
				{BkHostId: 9002, SubZone: "subzone-2", RackId: "rack-3"},
			},
			description: "cross rack",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.CurrentHostsByRack == nil || picker.MaxPerRack <= 0 {
					t.Errorf("expected rack tolerance initialized: %s", desc)
				}
			},
		},
		{
			name:        "MAJORITY_ELECTION_DISTRI",
			affinity:    MAJORITY_ELECTION_DISTRI,
			count:       5,
			description: "majority election distribution",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.PriorityElements == nil {
					t.Errorf("expected PriorityElements: %s", desc)
				}
			},
		},
		{
			name:           "SPECIAL_HOST_IDS",
			affinity:       NONE,
			count:          3,
			specialHostIds: []int{1001, 1002, 2001},
			description:    "special host ids provided",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if len(picker.SatisfiedHostIds) == 0 || picker.Count != 3 {
					t.Errorf("expected satisfied host ids and count 3: %s", desc)
				}
			},
		},
		{
			name:        "INVALID_AFFINITY",
			affinity:    "INVALID_AFFINITY",
			count:       3,
			description: "invalid affinity does not change count",
			validateFunc: func(t *testing.T, picker *MockPickerObject, desc string) {
				if picker.Count != 3 {
					t.Errorf("expected count unchanged: %s", desc)
				}
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ctx := &MockSearchContext{
				ObjectDetail: &MockObjectDetail{
					BkCloudId:    0,
					GroupMark:    "test-group",
					Count:        tc.count,
					Affinity:     tc.affinity,
					Tolerance:    tc.tolerance,
					CurrentHosts: tc.currentHosts,
					Spec:         MockSpec{Cpu: MockMeasureRange{Min: 16, Max: 16}, Mem: MockMeasureRange{Min: 64, Max: 64}},
					LocationSpec: MockLocationSpec{City: "深圳", SubZoneIds: []string{}},
				},
				RsType:           "mysql",
				IntentionBkBizId: 1001,
				IdcCitys:         []string{"city-1"},
				SpecialHostIds:   tc.specialHostIds,
			}

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

			err := MockPickInstanceBase(ctx, picker, items)
			if tc.expectError && err == nil {
				t.Fatalf("expected error but got none: %s", tc.description)
			}
			if !tc.expectError && err != nil {
				t.Fatalf("unexpected error: %v (%s)", err, tc.description)
			}
			if tc.validateFunc != nil {
				tc.validateFunc(t, picker, tc.description)
			}
		})
	}
}

// createMockItems returns a mocked resource pool
func createMockItems() []MockTbRpDetail {
	baseTime := time.Now()
	return []MockTbRpDetail{
		{BkHostID: 1001, IP: "192.168.1.1", AssetID: "asset-001", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "subzone-1", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 1002, IP: "192.168.1.2", AssetID: "asset-002", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "subzone-1", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 1003, IP: "192.168.1.3", AssetID: "asset-003", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "subzone-1", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 1004, IP: "192.168.1.4", AssetID: "asset-004", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "subzone-1", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 2001, IP: "192.168.2.1", AssetID: "asset-005", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "subzone-2", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 2002, IP: "192.168.2.2", AssetID: "asset-006", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "subzone-2", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 2003, IP: "192.168.2.3", AssetID: "asset-007", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "subzone-2", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 2004, IP: "192.168.2.4", AssetID: "asset-008", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "subzone-2", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 3001, IP: "192.168.3.1", AssetID: "asset-009", CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "subzone-3", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
		{BkHostID: 3002, IP: "192.168.3.2", AssetID: "asset-010", CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "subzone-3", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime},
	}
}
