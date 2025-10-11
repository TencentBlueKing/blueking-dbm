package apply

import (
	"fmt"
	"sort"
	"strings"
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// mockTbRpDetailItems 创建模拟的TbRpDetail数据
func mockTbRpDetailItems() []model.TbRpDetail {
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

// buildIndexByHost 构造 BkHostID -> 详情 的索引
func buildIndexByHost(items []model.TbRpDetail) map[int]model.TbRpDetail {
	m := make(map[int]model.TbRpDetail, len(items))
	for _, it := range items {
		m[it.BkHostID] = it
	}
	return m
}

// 新增：将二级分布以更直观的树形文本渲染（外层/内层均排序）
func renderTree(header string, m map[string]map[string]int) string {
	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n")
	outer := make([]string, 0, len(m))
	for k := range m {
		outer = append(outer, k)
	}
	sort.Strings(outer)
	for _, ok := range outer {
		inner := m[ok]
		// 求和
		sum := 0
		for _, v := range inner {
			sum += v
		}
		b.WriteString(fmt.Sprintf("- %s (total=%d)\n", ok, sum))
		inKeys := make([]string, 0, len(inner))
		for k := range inner {
			inKeys = append(inKeys, k)
		}
		sort.Strings(inKeys)
		for _, ik := range inKeys {
			b.WriteString(fmt.Sprintf("  • %s: %d\n", ik, inner[ik]))
		}
	}
	return b.String()
}

// 新增：将一层分布渲染为更直观的排序列表
func renderFlat(header string, m map[string]int) string {
	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n")
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		b.WriteString(fmt.Sprintf("- %s: %d\n", k, m[k]))
	}
	return b.String()
}

// 新增：园区->机架->主机ID 树形可视化（外层/内层排序，展示主机ID列表与计数）
func renderTreeHosts(header string, m map[string]map[string][]int) string {
	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n")
	outer := make([]string, 0, len(m))
	for k := range m {
		outer = append(outer, k)
	}
	sort.Strings(outer)
	for _, ok := range outer {
		inner := m[ok]
		// 主机总数
		hostSum := 0
		for _, hosts := range inner {
			hostSum += len(hosts)
		}
		b.WriteString(fmt.Sprintf("- %s (hosts=%d, racks=%d)\n", ok, hostSum, len(inner)))
		inKeys := make([]string, 0, len(inner))
		for k := range inner {
			inKeys = append(inKeys, k)
		}
		sort.Strings(inKeys)
		for _, rack := range inKeys {
			hosts := inner[rack]
			sort.Ints(hosts)
			b.WriteString(fmt.Sprintf("  • %s: count=%d, hosts=%v\n", rack, len(hosts), hosts))
		}
	}
	return b.String()
}

// logPickedRacks 输出本次申请到的主机对应的机架ID集合，以及主机->机架的映射
func logPickedRacks(t *testing.T, items []model.TbRpDetail, picker *PickerObject) {
	idx := buildIndexByHost(items)
	// 园区->机架->主机ID
	bySubZoneRackHosts := make(map[string]map[string][]int)
	// 机架计数汇总
	rackCount := make(map[string]int)
	for _, hid := range picker.SatisfiedHostIds {
		if it, ok := idx[hid]; ok {
			if _, ok := bySubZoneRackHosts[it.SubZoneID]; !ok {
				bySubZoneRackHosts[it.SubZoneID] = make(map[string][]int)
			}
			bySubZoneRackHosts[it.SubZoneID][it.RackID] = append(bySubZoneRackHosts[it.SubZoneID][it.RackID], hid)
			rackCount[it.RackID]++
		}
	}
	// 树形输出：园区->机架->主机ID
	t.Log("\n" + renderTreeHosts("[机架] 园区->机架->主机", bySubZoneRackHosts))
	// 排序汇总：机架ID及数量
	if len(rackCount) > 0 {
		t.Log("\n" + renderFlat("[机架] 机架ID统计", rackCount))
	}
}

// logDistribution 根据亲和性输出分布情况
// isRackLevel=true 输出: 园区(subzone) -> 机架(rack) 分布
// isRackLevel=false 输出: 城市(city) -> 园区(subzone) 分布
func logDistribution(t *testing.T, items []model.TbRpDetail, picker *PickerObject, isRackLevel bool) {
	idx := buildIndexByHost(items)

	// 如果没有拿到明确的主机列表，回退使用 PickDistribute/RackDistribute（更直观格式）
	if len(picker.SatisfiedHostIds) == 0 {
		if isRackLevel {
			// 仅有 subzone 汇总 + 机架汇总
			if len(picker.PickDistribute) > 0 {
				t.Log("\n" + renderFlat("[分布][机架级] 园区汇总(PickDistribute)", picker.PickDistribute))
			} else {
				t.Logf("[分布][机架级] 园区汇总(PickDistribute): %v", picker.PickDistribute)
			}
			if len(picker.RackDistribute) > 0 {
				t.Log("\n" + renderFlat("[分布][机架级] 机架汇总(RackDistribute)", picker.RackDistribute))
			} else {
				t.Logf("[分布][机架级] 机架汇总(RackDistribute): %v", picker.RackDistribute)
			}
			return
		}
		if len(picker.PickDistribute) > 0 {
			t.Log("\n" + renderFlat("[分布][园区级] 园区汇总(PickDistribute)", picker.PickDistribute))
		} else {
			t.Logf("[分布][园区级] 园区汇总(PickDistribute): %v", picker.PickDistribute)
		}
		return
	}

	if isRackLevel {
		bySubZoneRack := make(map[string]map[string]int)
		for _, hid := range picker.SatisfiedHostIds {
			if it, ok := idx[hid]; ok {
				sz := it.SubZoneID
				r := it.RackID
				if _, ok := bySubZoneRack[sz]; !ok {
					bySubZoneRack[sz] = make(map[string]int)
				}
				bySubZoneRack[sz][r]++
			}
		}
		// 更直观树形输出：园区 -> 机架
		t.Log("\n" + renderTree("[分布][机架级] 园区->机架", bySubZoneRack))
		return
	}

	// 园区级：城市->园区
	byCitySubZone := make(map[string]map[string]int)
	for _, hid := range picker.SatisfiedHostIds {
		if it, ok := idx[hid]; ok {
			city := it.City
			sz := it.SubZoneID
			if _, ok := byCitySubZone[city]; !ok {
				byCitySubZone[city] = make(map[string]int)
			}
			byCitySubZone[city][sz]++
		}
	}
	// 更直观树形输出：城市 -> 园区
	t.Log("\n" + renderTree("[分布][园区级] 城市->园区", byCitySubZone))
}

// createMockSearchContext 创建模拟的SearchContext
func createMockSearchContext(affinity string, count int, tolerance float64, currentHosts []CurrentResource) *SearchContext {
	return &SearchContext{
		ObjectDetail: &ObjectDetail{
			BkCloudId:    0,
			GroupMark:    "test-group",
			Count:        count,
			Affinity:     affinity,
			Tolerance:    tolerance,
			CurrentHosts: currentHosts,
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
	}
}

// createMockPickerObject 创建模拟的PickerObject
func createMockPickerObject(count int) *PickerObject {
	return &PickerObject{
		Item:                  "test-item",
		Count:                 count,
		PickDistribute:        make(map[string]int),
		SatisfiedHostIds:      []int{},
		SatisfiedHostIdsMap:   make(map[subZone][]int),
		PriorityElements:      make(map[subZone]*PriorityQueue),
		SubZonePrioritySumMap: make(map[subZone]int64),
		ExistRackIds:          []string{},
		ExistLinkNetdeviceIds: []string{},
		ProcessLogs:           []string{},
		RackDistribute:        make(map[string]int),
	}
}

// TestPickInstanceBase_NONE 测试无亲和性策略
func TestPickInstanceBase_NONE(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(NONE, 3, 0, nil)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_CROS_SUBZONE 测试跨园区亲和性策略
func TestPickInstanceBase_CROS_SUBZONE(t *testing.T) {
	items := mockTbRpDetailItems()

	ctx := createMockSearchContext(CROS_SUBZONE, 2, 0.5, nil)
	picker := createMockPickerObject(2)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 2 {
		t.Errorf("Expected count 2, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 验证容忍度配置已初始化
	if picker.TotalCount <= 0 {
		t.Error("Expected TotalCount to be greater than 0")
	}
	if picker.MaxPerSubZone <= 0 {
		t.Error("Expected MaxPerSubZone to be greater than 0")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

func TestPickInstanceBase_CROS_SUBZONE_WithCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()

	// 模拟当前已存在的主机
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

		{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
	}

	ctx := createMockSearchContext(CROS_SUBZONE, 4, 0.6, currentHosts)
	picker := createMockPickerObject(4)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 4 {
		t.Errorf("Expected count 4, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 验证容忍度配置已初始化
	if picker.TotalCount <= 0 {
		t.Error("Expected TotalCount to be greater than 0")
	}
	if picker.MaxPerSubZone <= 0 {
		t.Error("Expected MaxPerSubZone to be greater than 0")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_MAX_EACH_ZONE_EQUAL 测试每个园区尽量相等分配策略
func TestPickInstanceBase_MAX_EACH_ZONE_EQUAL(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(MAX_EACH_ZONE_EQUAL, 6, 0, nil)
	picker := createMockPickerObject(6)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 6 {
		t.Errorf("Expected count 6, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_SAME_SUBZONE 测试同园区亲和性策略
func TestPickInstanceBase_SAME_SUBZONE(t *testing.T) {
	items := mockTbRpDetailItems()

	// 模拟当前已存在的主机（同园区不同机架）
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

		{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
	}

	ctx := createMockSearchContext(SAME_SUBZONE, 3, 0.5, currentHosts)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 验证机架级容忍度配置已初始化
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	// 输出机架分布
	logDistribution(t, items, picker, true)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_SAME_SUBZONE_CROSS_SWTICH 测试同园区跨交换机策略
func TestPickInstanceBase_SAME_SUBZONE_CROSS_SWTICH(t *testing.T) {
	items := mockTbRpDetailItems()

	// 模拟当前已存在的主机（同园区同机架）
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

		{BkHostId: 9002, SubZone: "guangming", RackId: "rack-1"},
	}

	ctx := createMockSearchContext(SAME_SUBZONE_CROSS_SWTICH, 2, 0.5, currentHosts)
	picker := createMockPickerObject(2)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 2 {
		t.Errorf("Expected count 2, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 验证机架级容忍度配置已初始化
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	// 输出机架分布
	logDistribution(t, items, picker, true)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_CROSS_RACK 测试跨机架亲和性策略
func TestPickInstanceBase_CROSS_RACK(t *testing.T) {
	items := mockTbRpDetailItems()

	// 模拟当前已存在的主机（不同机架）
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

		{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
	}

	ctx := createMockSearchContext(CROSS_RACK, 4, 0.5, currentHosts)
	picker := createMockPickerObject(4)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 4 {
		t.Errorf("Expected count 4, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 验证机架级容忍度配置已初始化
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	// 输出机架分布
	logDistribution(t, items, picker, true)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_MAJORITY_ELECTION_DISTRI 测试多数选举分布策略
func TestPickInstanceBase_MAJORITY_ELECTION_DISTRI(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(MAJORITY_ELECTION_DISTRI, 5, 0, nil)
	picker := createMockPickerObject(5)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 5 {
		t.Errorf("Expected count 5, got %d", picker.Count)
	}
	if picker.PriorityElements == nil {
		t.Error("Expected PriorityElements to be initialized")
	}
	if picker.SubZonePrioritySumMap == nil {
		t.Error("Expected SubZonePrioritySumMap to be initialized")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_SpecialHostIds 测试指定主机ID场景
func TestPickInstanceBase_SpecialHostIds(t *testing.T) {
	items := mockTbRpDetailItems()

	ctx := createMockSearchContext(NONE, 3, 0, nil)
	// 设置指定的主机ID
	ctx.SpecialHostIds = []int{1001, 1002, 2001}
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	// 验证指定的主机ID被添加到满足条件的主机列表中
	contains1001 := false
	contains1002 := false
	contains2001 := false
	for _, id := range picker.SatisfiedHostIds {
		if id == 1001 {
			contains1001 = true
		}
		if id == 1002 {
			contains1002 = true
		}
		if id == 2001 {
			contains2001 = true
		}
	}
	if !contains1001 {
		t.Error("Expected SatisfiedHostIds to contain 1001")
	}
	if !contains1002 {
		t.Error("Expected SatisfiedHostIds to contain 1002")
	}
	if !contains2001 {
		t.Error("Expected SatisfiedHostIds to contain 2001")
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_EmptyItems 测试空资源列表场景
func TestPickInstanceBase_EmptyItems(t *testing.T) {
	items := []model.TbRpDetail{}
	ctx := createMockSearchContext(NONE, 3, 0, nil)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	// 空资源列表应该不会报错，但可能在后续处理中有问题
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	// 输出分布（无数据回退）
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_InvalidAffinity 测试无效亲和性策略
func TestPickInstanceBase_InvalidAffinity(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext("INVALID_AFFINITY", 3, 0, nil)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	// 无效的亲和性策略应该不会匹配任何case，函数应该正常返回
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_ZeroCount 测试零数量场景
func TestPickInstanceBase_ZeroCount(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(NONE, 0, 0, nil)
	picker := createMockPickerObject(0)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 0 {
		t.Errorf("Expected count 0, got %d", picker.Count)
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_HighTolerance 测试高容忍度场景
func TestPickInstanceBase_HighTolerance(t *testing.T) {
	items := mockTbRpDetailItems()

	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},
	}

	ctx := createMockSearchContext(CROS_SUBZONE, 3, 0.9, currentHosts)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	// 高容忍度应该允许更多机器在同一园区
	if picker.MaxPerSubZone <= 1 {
		t.Errorf("Expected MaxPerSubZone to be greater than 1, got %d", picker.MaxPerSubZone)
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_LowTolerance 测试低容忍度场景
func TestPickInstanceBase_LowTolerance(t *testing.T) {
	items := mockTbRpDetailItems()

	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},

		{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
	}

	ctx := createMockSearchContext(CROS_SUBZONE, 4, 0.1, currentHosts)
	picker := createMockPickerObject(4)

	err := ctx.PickInstanceBase(picker, items)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 4 {
		t.Errorf("Expected count 4, got %d", picker.Count)
	}
	// 低容忍度应该限制每个园区的机器数量
	if picker.MaxPerSubZone > 2 {
		t.Errorf("Expected MaxPerSubZone to be less than or equal to 2, got %d", picker.MaxPerSubZone)
	}
	// 输出园区分布
	logDistribution(t, items, picker, false)
	// 输出机架ID
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_SAME_SUBZONE_NoCurrentHosts 无当前主机的同园区策略
func TestPickInstanceBase_SAME_SUBZONE_NoCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(SAME_SUBZONE, 3, 0.5, nil)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_SAME_SUBZONE_CROSS_SWTICH_NoCurrentHosts 无当前主机的同园区跨交换机策略
func TestPickInstanceBase_SAME_SUBZONE_CROSS_SWTICH_NoCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(SAME_SUBZONE_CROSS_SWTICH, 2, 0.5, nil)
	picker := createMockPickerObject(2)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 2 {
		t.Errorf("Expected count 2, got %d", picker.Count)
	}
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_CROSS_RACK_NoCurrentHosts 无当前主机的跨机架策略
func TestPickInstanceBase_CROSS_RACK_NoCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(CROSS_RACK, 4, 0.5, nil)
	picker := createMockPickerObject(4)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 4 {
		t.Errorf("Expected count 4, got %d", picker.Count)
	}
	if picker.CurrentHostsByRack == nil {
		t.Error("Expected CurrentHostsByRack to be initialized")
	}
	if picker.MaxPerRack <= 0 {
		t.Error("Expected MaxPerRack to be greater than 0")
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_MAX_EACH_ZONE_EQUAL_WithCurrentHosts 有当前主机的“每园区尽量相等”策略
func TestPickInstanceBase_MAX_EACH_ZONE_EQUAL_WithCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},
		{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
	}
	ctx := createMockSearchContext(MAX_EACH_ZONE_EQUAL, 6, 0.0, currentHosts)
	picker := createMockPickerObject(6)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 6 {
		t.Errorf("Expected count 6, got %d", picker.Count)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_NONE_WithCurrentHosts 无亲和策略但有当前主机
func TestPickInstanceBase_NONE_WithCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},
	}
	ctx := createMockSearchContext(NONE, 3, 0.0, currentHosts)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_MAJORITY_ELECTION_DISTRI_WithCurrentHosts 多数选举策略（有当前主机）
func TestPickInstanceBase_MAJORITY_ELECTION_DISTRI_WithCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},
		{BkHostId: 9002, SubZone: "nanshan", RackId: "rack-3"},
	}
	ctx := createMockSearchContext(MAJORITY_ELECTION_DISTRI, 5, 0.0, currentHosts)
	picker := createMockPickerObject(5)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 5 {
		t.Errorf("Expected count 5, got %d", picker.Count)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_HighTolerance_NoCurrentHosts 高容忍度（无当前主机）
func TestPickInstanceBase_HighTolerance_NoCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(CROS_SUBZONE, 3, 0.9, nil)
	picker := createMockPickerObject(3)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 3 {
		t.Errorf("Expected count 3, got %d", picker.Count)
	}
	if picker.MaxPerSubZone <= 1 {
		t.Errorf("Expected MaxPerSubZone to be greater than 1, got %d", picker.MaxPerSubZone)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestPickInstanceBase_LowTolerance_NoCurrentHosts 低容忍度（无当前主机）
func TestPickInstanceBase_LowTolerance_NoCurrentHosts(t *testing.T) {
	items := mockTbRpDetailItems()
	ctx := createMockSearchContext(CROS_SUBZONE, 4, 0.1, nil)
	picker := createMockPickerObject(4)

	err := ctx.PickInstanceBase(picker, items)
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if picker.Count != 4 {
		t.Errorf("Expected count 4, got %d", picker.Count)
	}
	if picker.MaxPerSubZone > 2 {
		t.Errorf("Expected MaxPerSubZone to be less than or equal to 2, got %d", picker.MaxPerSubZone)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}
