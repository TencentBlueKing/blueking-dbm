package apply

import (
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
)

// 本文件仅测试“亲和性导致的不匹配”，不通过数量、规格、状态、城市等维度造成失败
// 约束：
// - 所有 mock 数据均满足 CPU=16/Mem=64、Status=Unused、City=city-1(深圳)
// - 失败原因仅来自 Affinity 策略本身

// TestUnmatchAffinity_CROS_SUBZONE_AllInOneSubzone
// 期望：需要跨园区，但所有资源均在同一园区，导致无法满足
func TestUnmatchAffinity_CROS_SUBZONE_AllInOneSubzone(t *testing.T) {
	items := []model.TbRpDetail{
		{BkHostID: 8001, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8002, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROS_SUBZONE, 2, 0.0, nil)
	picker := createMockPickerObject(2)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 1 {
		t.Fatalf("expect 0 matched hosts due to CROS_SUBZONE, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_SAME_SUBZONE_DifferentFromCurrent
// 期望：需要与当前主机同园区，但可用资源全部在不同园区，导致无法满足
func TestUnmatchAffinity_SAME_SUBZONE_DifferentFromCurrent(t *testing.T) {
	items := []model.TbRpDetail{
		// 资源都在
		{BkHostID: 8101, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8102, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	current := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	ctx := createMockSearchContext(SAME_SUBZONE, 2, 0.0, current)
	picker := createMockPickerObject(2)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 0 {
		t.Fatalf("expect 0 matched hosts due to SAME_SUBZONE, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_SAME_SUBZONE_CROSS_SWTICH_OnlyOneSwitch
// 期望：同园区跨交换机，但仅提供一个交换机，导致无法满足
func TestUnmatchAffinity_SAME_SUBZONE_CROSS_SWTICH_OnlyOneSwitch(t *testing.T) {
	items := []model.TbRpDetail{
		// 都在 guangming，且只有 switch-1
		{BkHostID: 8201, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8202, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	current := []CurrentResource{{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"}}
	ctx := createMockSearchContext(SAME_SUBZONE_CROSS_SWTICH, 2, 0.0, current)
	picker := createMockPickerObject(2)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 0 {
		t.Fatalf("expect 0 matched hosts due to SAME_SUBZONE_CROSS_SWTICH, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_RACK_AllInSameRack
// 期望：需要跨机架，但资源均在同一机架，导致无法满足
func TestUnmatchAffinity_CROSS_RACK_AllInSameRack(t *testing.T) {
	items := []model.TbRpDetail{
		{BkHostID: 8301, CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8302, CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_RACK, 2, 0.0, nil)
	picker := createMockPickerObject(2)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(picker.SatisfiedHostIds) != 1 {
		t.Fatalf("expect 0 matched hosts due to CROSS_RACK, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, true)
	logPickedRacks(t, items, picker)
}
