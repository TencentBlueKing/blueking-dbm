package apply

import (
	"fmt"
	"sort"
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// logPreResources 输出测试前可用资源的分布（城市→园区→机架→主机）
func logPreResources(t *testing.T, items []model.TbRpDetail) {
	t.Helper()
	// city -> subzone -> rack -> hostIDs
	tree := make(map[string]map[string]map[string][]int)
	for _, it := range items {
		city := it.City
		sub := it.SubZoneID
		rack := it.RackID
		if _, ok := tree[city]; !ok {
			tree[city] = make(map[string]map[string][]int)
		}
		if _, ok := tree[city][sub]; !ok {
			tree[city][sub] = make(map[string][]int)
		}
		tree[city][sub][rack] = append(tree[city][sub][rack], it.BkHostID)
	}

	// 排序输出，增强可读性
	cities := make([]string, 0, len(tree))
	for c := range tree {
		cities = append(cities, c)
	}
	sort.Strings(cities)

	t.Log("===== 预分布（测试前资源）=====")
	for _, c := range cities {
		subs := make([]string, 0, len(tree[c]))
		for s := range tree[c] {
			subs = append(subs, s)
		}
		sort.Strings(subs)
		// 统计城市总量
		cityTotal := 0
		for _, s := range subs {
			for _, hosts := range tree[c][s] {
				cityTotal += len(hosts)
			}
		}
		t.Logf("城市: %s (总主机: %d)", c, cityTotal)
		for _, s := range subs {
			racks := make([]string, 0, len(tree[c][s]))
			for r := range tree[c][s] {
				racks = append(racks, r)
			}
			sort.Strings(racks)
			// 统计园区
			subTotal := 0
			for _, r := range racks {
				subTotal += len(tree[c][s][r])
			}
			t.Logf("  园区(SubZoneID): %s (主机: %d)", s, subTotal)
			for _, r := range racks {
				hosts := append([]int(nil), tree[c][s][r]...)
				sort.Ints(hosts)
				t.Logf("    机架: %s -> 主机: %v (数量: %d)", r, hosts, len(hosts))
			}
		}
	}
	// 汇总机架/园区层面的平面统计，便于快速观测
	subSummary := map[string]int{}
	rackSummary := map[string]int{}
	for _, c := range cities {
		for s, racks := range tree[c] {
			for r, hosts := range racks {
				subSummary[s] += len(hosts)
				rackSummary[r] += len(hosts)
			}
		}
	}
	orderedSub := make([]string, 0, len(subSummary))
	for s := range subSummary {
		orderedSub = append(orderedSub, s)
	}
	sort.Strings(orderedSub)
	orderedRack := make([]string, 0, len(rackSummary))
	for r := range rackSummary {
		orderedRack = append(orderedRack, r)
	}
	sort.Strings(orderedRack)
	var subPairs []string
	for _, s := range orderedSub {
		subPairs = append(subPairs, fmt.Sprintf("%s:%d", s, subSummary[s]))
	}
	var rackPairs []string
	for _, r := range orderedRack {
		rackPairs = append(rackPairs, fmt.Sprintf("%s:%d", r, rackSummary[r]))
	}
	t.Logf("[汇总] 园区(SubZoneID) -> 数量: %v", subPairs)
	t.Logf("[汇总] 机架(RackID) -> 数量: %v", rackPairs)
}

// makeSparseItems_NONE 返回刚好满足 NONE 策略的最小数据：任意 3 台
func makeSparseItems_NONE() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 101, IP: "127.0.0.1", AssetID: "a-101", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 102, IP: "127.0.0.2", AssetID: "a-102", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 103, IP: "127.0.0.2", AssetID: "a-103", CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// makeSparseItems_CROS_SUBZONE 返回刚好满足跨园区：两个不同 subzone 各 1 台
func makeSparseItems_CROS_SUBZONE() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 201, IP: "127.0.0.1", AssetID: "a-201", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 202, IP: "127.0.0.2", AssetID: "a-202", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// makeSparseItems_MAX_EACH_ZONE_EQUAL 刚好满足每园区尽量相等：两个 subzone，各 2 台
func makeSparseItems_MAX_EACH_ZONE_EQUAL() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 301, IP: "127.0.0.1", AssetID: "a-301", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 302, IP: "127.0.0.2", AssetID: "a-302", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 303, IP: "127.0.0.2", AssetID: "a-303", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 304, IP: "127.0.0.2", AssetID: "a-304", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// makeSparseItems_SAME_SUBZONE 刚好满足同园区：同一个 subzone 两台，不同机架
func makeSparseItems_SAME_SUBZONE() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 401, IP: "127.0.0.1", AssetID: "a-401", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 402, IP: "127.0.0.2", AssetID: "a-402", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// makeSparseItems_SAME_SUBZONE_CROSS_SWITCH 刚好满足同园区跨交换机：同 subzone 两台，两个不同 switch/rack
func makeSparseItems_SAME_SUBZONE_CROSS_SWITCH() []model.TbRpDetail {
	return makeSparseItems_SAME_SUBZONE()
}

// makeSparseItems_CROSS_RACK 刚好满足跨机架：至少两个不同机架
func makeSparseItems_CROSS_RACK() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 501, IP: "127.0.0.1", AssetID: "a-501", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 502, IP: "127.0.0.2", AssetID: "a-502", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// makeSparseItems_MAJORITY_ELECTION_DISTRI 刚好满足多数选举：三个园区共 5 台，分布不均以测试选举
func makeSparseItems_MAJORITY_ELECTION_DISTRI() []model.TbRpDetail {
	base := time.Now()
	return []model.TbRpDetail{
		{BkHostID: 601, IP: "127.0.0.1", AssetID: "a-601", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 602, IP: "127.0.0.2", AssetID: "a-602", CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 603, IP: "127.0.0.2", AssetID: "a-603", CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 604, IP: "127.0.0.2", AssetID: "a-604", CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
		{BkHostID: 605, IP: "127.0.0.2", AssetID: "a-605", CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-6", NetDeviceID: "switch-6", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: base},
	}
}

// createSparseContext 生成极端场景用的 SearchContext
func createSparseContext(affinity string, count int, tolerance float64, current []CurrentResource) *SearchContext {
	return &SearchContext{
		ObjectDetail: &ObjectDetail{
			BkCloudId:    0,
			GroupMark:    "extreme-group",
			Count:        count,
			Affinity:     affinity,
			Tolerance:    tolerance,
			CurrentHosts: current,
			Spec: meta.Spec{
				Cpu: meta.MeasureRange{Min: 16, Max: 16},
				Mem: meta.MeasureRange{Min: 64, Max: 64},
			},
			LocationSpec: meta.LocationSpec{City: "深圳"},
		},
		RsType:           "mysql",
		IntentionBkBizId: 1001,
		IdcCitys:         []string{"city-1"},
	}
}

// ------- 极端场景用例（每种亲和性单独构造 mock 数据）-------

func TestExtreme_NONE_Minimal(t *testing.T) {
	items := makeSparseItems_NONE()
	logPreResources(t, items)
	ctx := createSparseContext(NONE, 3, 0, nil)
	picker := createMockPickerObject(3)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("NONE minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 3 {
		t.Errorf("expect 3 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

func TestExtreme_CROS_SUBZONE_Minimal(t *testing.T) {
	items := makeSparseItems_CROS_SUBZONE()
	logPreResources(t, items)
	ctx := createSparseContext(CROS_SUBZONE, 2, 0.0, nil)
	picker := createMockPickerObject(2)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("CROS_SUBZONE minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 2 {
		t.Errorf("expect 2 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

func TestExtreme_MAX_EACH_ZONE_EQUAL_Minimal(t *testing.T) {
	items := makeSparseItems_MAX_EACH_ZONE_EQUAL()
	logPreResources(t, items)
	ctx := createSparseContext(MAX_EACH_ZONE_EQUAL, 4, 0.0, nil)
	picker := createMockPickerObject(4)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("MAX_EACH_ZONE_EQUAL minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 4 {
		t.Errorf("expect 4 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

func TestExtreme_SAME_SUBZONE_Minimal_WithCurrent(t *testing.T) {
	items := makeSparseItems_SAME_SUBZONE()
	logPreResources(t, items)
	current := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	ctx := createSparseContext(SAME_SUBZONE, 2, 0.5, current)
	picker := createMockPickerObject(2)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("SAME_SUBZONE minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 2 {
		t.Errorf("expect 2 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

func TestExtreme_SAME_SUBZONE_CROSS_SWTICH_Minimal(t *testing.T) {
	items := makeSparseItems_SAME_SUBZONE_CROSS_SWITCH()
	logPreResources(t, items)
	current := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	ctx := createSparseContext(SAME_SUBZONE_CROSS_SWTICH, 2, 0.5, current)
	picker := createMockPickerObject(2)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("SAME_SUBZONE_CROSS_SWTICH minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 2 {
		t.Errorf("expect 2 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

func TestExtreme_CROSS_RACK_Minimal_WithCurrent(t *testing.T) {
	items := makeSparseItems_CROSS_RACK()
	logPreResources(t, items)
	current := []CurrentResource{{BkHostId: 9001, SubZone: "nanshan", RackId: "rack-3"}}
	ctx := createSparseContext(CROSS_RACK, 2, 0.5, current)
	picker := createMockPickerObject(2)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("CROSS_RACK minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 2 {
		t.Errorf("expect 2 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

func TestExtreme_MAJORITY_ELECTION_DISTRI_Minimal(t *testing.T) {
	items := makeSparseItems_MAJORITY_ELECTION_DISTRI()
	logPreResources(t, items)
	ctx := createSparseContext(MAJORITY_ELECTION_DISTRI, 5, 0.0, nil)
	picker := createMockPickerObject(5)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("MAJORITY_ELECTION_DISTRI minimal: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 5 {
		t.Errorf("expect 5 picked, got %d", len(picker.SatisfiedHostIds))
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// runAffinitySplit 统一跑某个亲和性的多容忍度/当前主机变体
func runAffinitySplit(t *testing.T, name string, items []model.TbRpDetail, affinity string, want int, currents [][]CurrentResource, isRackLevel bool) {
	t.Helper()
	tols := []float64{0.5, 0.9}
	for _, tol := range tols {
		for idx, cur := range currents {
			label := fmt.Sprintf("tol=%.1f", tol)
			if cur != nil {
				label += fmt.Sprintf("/withCurrent#%d", idx+1)
			} else {
				label += "/noCurrent"
			}
			t.Run(label, func(t *testing.T) {
				logPreResources(t, items)
				ctx := createSparseContext(affinity, want, tol, cur)
				picker := createMockPickerObject(want)
				if err := ctx.PickInstanceBase(picker, items); err != nil {
					t.Fatalf("%s %s: %v", name, label, err)
				}
				if got := len(picker.SatisfiedHostIds); got != want {
					t.Errorf("%s %s expect %d, got %d", name, label, want, got)
				}
				logDistribution(t, items, picker, isRackLevel)
				logPickedRacks(t, items, picker)
			})
		}
	}
}

func TestAffinity_NONE(t *testing.T) {
	items := makeSparseItems_NONE()
	runAffinitySplit(t, "NONE", items, NONE, 3, [][]CurrentResource{nil}, false)
}

func TestAffinity_CROS_SUBZONE(t *testing.T) {
	items := makeSparseItems_CROS_SUBZONE()
	runAffinitySplit(t, "CROS_SUBZONE", items, CROS_SUBZONE, 2, [][]CurrentResource{nil}, false)
}

func TestAffinity_MAX_EACH_ZONE_EQUAL(t *testing.T) {
	items := makeSparseItems_MAX_EACH_ZONE_EQUAL()
	runAffinitySplit(t, "MAX_EACH_ZONE_EQUAL", items, MAX_EACH_ZONE_EQUAL, 4, [][]CurrentResource{nil}, false)
}

func TestAffinity_SAME_SUBZONE(t *testing.T) {
	items := makeSparseItems_SAME_SUBZONE()
	noCurrent := []CurrentResource(nil)
	withCurrent := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	runAffinitySplit(t, "SAME_SUBZONE", items, SAME_SUBZONE, 2, [][]CurrentResource{noCurrent, withCurrent}, true)
}

func TestAffinity_SAME_SUBZONE_CROSS_SWTICH(t *testing.T) {
	items := makeSparseItems_SAME_SUBZONE_CROSS_SWITCH()
	noCurrent := []CurrentResource(nil)
	withCurrent := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	runAffinitySplit(t, "SAME_SUBZONE_CROSS_SWTICH", items, SAME_SUBZONE_CROSS_SWTICH, 2, [][]CurrentResource{noCurrent, withCurrent}, true)
}

func TestAffinity_CROSS_RACK(t *testing.T) {
	items := makeSparseItems_CROSS_RACK()
	noCurrent := []CurrentResource(nil)
	withCurrent := []CurrentResource{{BkHostId: 9001, SubZone: "nanshan", RackId: "rack-3"}}
	runAffinitySplit(t, "CROSS_RACK", items, CROSS_RACK, 2, [][]CurrentResource{noCurrent, withCurrent}, true)
}

func TestAffinity_MAJORITY_ELECTION_DISTRI(t *testing.T) {
	items := makeSparseItems_MAJORITY_ELECTION_DISTRI()
	runAffinitySplit(t, "MAJORITY_ELECTION_DISTRI", items, MAJORITY_ELECTION_DISTRI, 5, [][]CurrentResource{nil}, false)
}
