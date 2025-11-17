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

// TestUnmatchAffinity_CROSS_SUBZONE_STRONG_LessThanThreeSubzones
// 期望：跨园区(强)需要至少3个园区，但只有2个园区可用，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_STRONG_LessThanThreeSubzones(t *testing.T) {
	items := []model.TbRpDetail{
		{BkHostID: 8401, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8402, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8403, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8404, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_STRONG, 6, 0, nil)
	picker := createMockPickerObject(6)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于只有2个园区，无法满足至少3个园区的要求，应该无法匹配到6台机器
	if len(picker.SatisfiedHostIds) >= 6 {
		t.Fatalf("expect less than 6 matched hosts due to insufficient subzones, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_SUBZONE_STRONG_ExceedSubzoneTolerance
// 期望：跨园区(强)园区容忍度1/3，某个园区超过容忍度限制，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_STRONG_ExceedSubzoneTolerance(t *testing.T) {
	items := []model.TbRpDetail{
		// 光明园区：4台机器（超过容忍度1/3，6台机器最多2台）
		{BkHostID: 8501, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8502, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8503, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8504, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 南山园区：1台机器
		{BkHostID: 8505, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 福田园区：1台机器
		{BkHostID: 8506, CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-6", NetDeviceID: "switch-6", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_STRONG, 6, 0, nil)
	picker := createMockPickerObject(6)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于光明园区超过容忍度限制，应该无法匹配到6台机器
	if len(picker.SatisfiedHostIds) >= 6 {
		t.Fatalf("expect less than 6 matched hosts due to subzone tolerance exceeded, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_SUBZONE_STRONG_ExceedRackTolerance
// 期望：跨园区(强)机架容忍度1/2，某个机架超过容忍度限制，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_STRONG_ExceedRackTolerance(t *testing.T) {
	items := []model.TbRpDetail{
		// 光明园区rack-1：4台机器（超过容忍度1/2，6台机器最多3台）
		{BkHostID: 8601, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8602, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8603, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8604, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 南山园区rack-2：1台机器
		{BkHostID: 8605, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 福田园区rack-3：1台机器
		{BkHostID: 8606, CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_STRONG, 6, 0, nil)
	picker := createMockPickerObject(6)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于rack-1超过容忍度限制，应该无法匹配到6台机器
	if len(picker.SatisfiedHostIds) >= 6 {
		t.Fatalf("expect less than 6 matched hosts due to rack tolerance exceeded, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_SUBZONE_STRONG_WithCurrentHosts_ExceedTolerance
// 期望：有current_hosts时，考虑总数量后超过容忍度限制，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_STRONG_WithCurrentHosts_ExceedTolerance(t *testing.T) {
	items := []model.TbRpDetail{
		// 光明园区：3台可用机器
		{BkHostID: 8701, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8702, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8703, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 南山园区：2台可用机器
		{BkHostID: 8704, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8705, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-5", NetDeviceID: "switch-5", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 福田园区：1台可用机器
		{BkHostID: 8706, CityID: "city-1", City: "深圳", SubZone: "福田", SubZoneID: "futian", RackID: "rack-6", NetDeviceID: "switch-6", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	// 当前已有3台机器在光明园区（加上申请的6台，总共9台，光明园区最多3台，但已有3台）
	currentHosts := []CurrentResource{
		{BkHostId: 9001, SubZone: "guangming", RackId: "rack-1"},
		{BkHostId: 9002, SubZone: "guangming", RackId: "rack-2"},
		{BkHostId: 9003, SubZone: "guangming", RackId: "rack-3"},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_STRONG, 6, 0, currentHosts)
	picker := createMockPickerObject(6)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于光明园区已有3台机器，加上新申请的会超过容忍度（9*1/3=3），应该无法匹配到6台机器
	if len(picker.SatisfiedHostIds) >= 6 {
		t.Fatalf("expect less than 6 matched hosts due to subzone tolerance exceeded with current hosts, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_SUBZONE_WEAK_LessThanTwoSubzones
// 期望：跨园区(弱)需要至少2个园区，但只有1个园区可用，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_WEAK_LessThanTwoSubzones(t *testing.T) {
	items := []model.TbRpDetail{
		{BkHostID: 8801, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8802, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8803, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8804, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 4, 0, nil)
	picker := createMockPickerObject(4)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于只有1个园区，无法满足至少2个园区的要求，应该无法匹配到4台机器
	if len(picker.SatisfiedHostIds) >= 4 {
		t.Fatalf("expect less than 4 matched hosts due to insufficient subzones, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// TestUnmatchAffinity_CROSS_SUBZONE_WEAK_ExceedSubzoneTolerance
// 期望：跨园区(弱)园区容忍度1/2，某个园区超过容忍度限制，导致无法满足
func TestUnmatchAffinity_CROSS_SUBZONE_WEAK_ExceedSubzoneTolerance(t *testing.T) {
	items := []model.TbRpDetail{
		// 光明园区：3台机器（超过容忍度1/2，4台机器最多2台）
		{BkHostID: 8901, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-1", NetDeviceID: "switch-1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8902, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-2", NetDeviceID: "switch-2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		{BkHostID: 8903, CityID: "city-1", City: "深圳", SubZone: "光明", SubZoneID: "guangming", RackID: "rack-3", NetDeviceID: "switch-3", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
		// 南山园区：1台机器
		{BkHostID: 8904, CityID: "city-1", City: "深圳", SubZone: "南山", SubZoneID: "nanshan", RackID: "rack-4", NetDeviceID: "switch-4", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: time.Now()},
	}
	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 4, 0, nil)
	picker := createMockPickerObject(4)

	logPreResources(t, items)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	// 由于光明园区超过容忍度限制，应该无法匹配到4台机器
	if len(picker.SatisfiedHostIds) >= 4 {
		t.Fatalf("expect less than 4 matched hosts due to subzone tolerance exceeded, got %d: %v", len(picker.SatisfiedHostIds), picker.SatisfiedHostIds)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}
