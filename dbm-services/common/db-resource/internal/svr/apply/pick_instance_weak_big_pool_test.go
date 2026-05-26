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
	"slices"
	"sort"
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/model"
)

// =====================================================================
// 测试 CROSS_SUBZONE_WEAK 大池子优先分配（pickerCrossSubzoneBigPoolFirst）
// =====================================================================
//
// 算法核心：
//  1. 按 subzone 剩余库存量降序排序
//  2. 在最大 subzone 内连续取，直到达到 MaxPerSubZone 或库存耗尽
//  3. 切到下一个大 subzone 继续，直到 PickerDone
//
// 设计动机：真实生产场景下（n 较小、多组顺序消耗）纯均衡策略会过早把小池子
//   消耗到归零，导致末尾组只剩 1 个 subzone 凑不齐 WEAK 约束。
//   BigPoolFirst 让大池子吃满 MaxPerSubZone 上限，把小池子留给后续组使用。
//
// 关键参数（subzone 容忍度 0.5、rack 容忍度 0.5）：
//   - n=3：MaxPerSubZone=2, MaxPerRack=1
//   - n=4：MaxPerSubZone=2, MaxPerRack=1
//   - n=6：MaxPerSubZone=3, MaxPerRack=2

// mockWeakPoolItems 构造典型场景：三个 subzone 库存不均
//
//	大池 bigzone  : 10 台（rack-bz-1..rack-bz-10，每台一 rack）
//	中池 midzone  : 5 台 （rack-mz-1..rack-mz-5）
//	小池 smallzone: 2 台 （rack-sz-1, rack-sz-2）
func mockWeakPoolItems() []model.TbRpDetail {
	baseTime := time.Now()
	items := make([]model.TbRpDetail, 0, 17)
	hid := 10000
	build := func(subzone string, rackPrefix string, count int) {
		for i := 1; i <= count; i++ {
			hid++
			items = append(items, model.TbRpDetail{
				BkHostID:    hid,
				IP:          fmt.Sprintf("127.0.0.%d", hid-10000),
				AssetID:     fmt.Sprintf("asset-%d", hid),
				CityID:      "city-1",
				City:        "深圳",
				SubZone:     subzone,
				SubZoneID:   subzone,
				RackID:      fmt.Sprintf("%s-%d", rackPrefix, i),
				NetDeviceID: fmt.Sprintf("switch-%s-%d", rackPrefix, i),
				CPUNum:      16,
				DramCap:     64,
				Status:      "Unused",
				CreateTime:  baseTime,
			})
		}
	}
	build("bigzone", "rack-bz", 10)
	build("midzone", "rack-mz", 5)
	build("smallzone", "rack-sz", 2)
	return items
}

// countBySubzone 统计已分配主机在每个 subzone 的数量
func countBySubzone(items []model.TbRpDetail, picker *PickerObject) map[string]int {
	idx := make(map[int]model.TbRpDetail, len(items))
	for _, it := range items {
		idx[it.BkHostID] = it
	}
	result := make(map[string]int)
	for _, hid := range picker.SatisfiedHostIds {
		if it, ok := idx[hid]; ok {
			result[it.SubZoneID]++
		}
	}
	return result
}

// removeHostsFromItems 从 items 中移除已被选中的 host，模拟连续单据消耗库存
func removeHostsFromItems(items []model.TbRpDetail, removeIds []int) []model.TbRpDetail {
	result := make([]model.TbRpDetail, 0, len(items))
	for _, it := range items {
		if !slices.Contains(removeIds, it.BkHostID) {
			result = append(result, it)
		}
	}
	return result
}

// ------------------------------------------------------------------------
// Case 1：基础场景 —— 大池吃满 tolerance，小池被完整保护
// ------------------------------------------------------------------------
// 库存：bigzone=10, midzone=5, smallzone=2；申请 4 台 WEAK
// MaxPerSubZone=ceil(4*0.5)=2, MaxPerRack=1
//
// BigPoolFirst 执行：
//  1. 按剩余库存降序 → [bigzone, midzone, smallzone]
//  2. bigzone 取 2（达 MaxPerSubZone=2）
//  3. midzone 取 2（达 MaxPerSubZone=2）→ PickerDone
//
// 期望最终：bigzone=2, midzone=2, smallzone=0（小池完全保护）
func TestWeakBigPool_BasicLargestFirst(t *testing.T) {
	items := mockWeakPoolItems()
	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 4, 0, nil)
	picker := createMockPickerObject(4)

	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("PickInstanceBase error: %v", err)
	}

	if got := len(picker.SatisfiedHostIds); got != 4 {
		t.Fatalf("Expected 4 hosts, got %d", got)
	}
	if picker.MaxPerSubZone != 2 {
		t.Fatalf("Expected MaxPerSubZone=2, got %d", picker.MaxPerSubZone)
	}

	dist := countBySubzone(items, picker)
	// bigzone 必须吃满 MaxPerSubZone=2
	if dist["bigzone"] != 2 {
		t.Errorf("Expected bigzone=2 (BigPoolFirst fills to MaxPerSubZone), got %d (dist=%v)",
			dist["bigzone"], dist)
	}
	// midzone 必须吃满 MaxPerSubZone=2
	if dist["midzone"] != 2 {
		t.Errorf("Expected midzone=2 (BigPoolFirst second pool fills to limit), got %d (dist=%v)",
			dist["midzone"], dist)
	}
	// smallzone 完全保护（前两池已满足）
	if dist["smallzone"] != 0 {
		t.Errorf("Expected smallzone=0 (preserved for later groups), got %d (dist=%v)",
			dist["smallzone"], dist)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// ------------------------------------------------------------------------
// Case 2：中等需求 —— 大池+中池吃满 tolerance，小池被完整保护
// ------------------------------------------------------------------------
// 库存同上；申请 6 台 WEAK；MaxPerSubZone=ceil(6*0.5)=3, MaxPerRack=2
//
// BigPoolFirst 执行：
//  1. 按剩余库存降序 → [bigzone, midzone, smallzone]
//  2. bigzone 取 3（达 MaxPerSubZone=3）
//  3. midzone 取 3（达 MaxPerSubZone=3）→ PickerDone
//
// 期望最终：bigzone=3, midzone=3, smallzone=0（小池完全保护）
func TestWeakBigPool_PreserveSmallPool(t *testing.T) {
	items := mockWeakPoolItems()
	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 6, 0, nil)
	picker := createMockPickerObject(6)

	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("PickInstanceBase error: %v", err)
	}

	if got := len(picker.SatisfiedHostIds); got != 6 {
		t.Fatalf("Expected 6 hosts, got %d", got)
	}
	if picker.MaxPerSubZone != 3 {
		t.Fatalf("Expected MaxPerSubZone=3, got %d", picker.MaxPerSubZone)
	}

	dist := countBySubzone(items, picker)
	// bigzone 吃满 MaxPerSubZone=3
	if dist["bigzone"] != 3 {
		t.Errorf("Expected bigzone=3 (BigPoolFirst fills largest pool first), got %d (dist=%v)",
			dist["bigzone"], dist)
	}
	// midzone 吃满 MaxPerSubZone=3
	if dist["midzone"] != 3 {
		t.Errorf("Expected midzone=3 (BigPoolFirst second pool fills to limit), got %d (dist=%v)",
			dist["midzone"], dist)
	}
	// smallzone 完全不取（前两池已满足需求）
	if dist["smallzone"] != 0 {
		t.Errorf("Expected smallzone=0 (preserved for later groups), got %d (dist=%v)",
			dist["smallzone"], dist)
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// ------------------------------------------------------------------------
// Case 3：真实场景模拟 —— 5 组单据连续申请 3 台 WEAK，验证不会因小池耗尽失败
// ------------------------------------------------------------------------
// 库存：bigzone=10, midzone=5, smallzone=2 (共17台)
// 连续 5 次单据，每次申请 3 台（n=3 → MaxPerSubZone=2, MaxPerRack=1）
// 总需求 15 台 ≤ 库存 17 台
//
// BigPoolFirst 策略下：
//   - 前 4 单：bigzone=2 + midzone=1（big/mid 优先，small 完全保护）
//   - 第 5 单：bigzone 剩 2 / midzone 剩 1 / smallzone 剩 2 → 取大池组合
//
// 验证：5 单全部成功
func TestWeakBigPool_FiveSequentialGroups(t *testing.T) {
	items := mockWeakPoolItems()
	const groupCount = 5
	const perGroup = 3

	successCount := 0
	for g := 1; g <= groupCount; g++ {
		ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, perGroup, 0, nil)
		picker := createMockPickerObject(perGroup)
		err := ctx.PickInstanceBase(picker, items)
		if err != nil {
			t.Logf("group %d failed: %v (剩余库存:%d)", g, err, len(items))
			continue
		}
		if len(picker.SatisfiedHostIds) != perGroup {
			t.Logf("group %d got %d/%d hosts", g, len(picker.SatisfiedHostIds), perGroup)
			continue
		}
		successCount++
		dist := countBySubzone(items, picker)
		t.Logf("group %d OK, dist=%v, picked=%v", g, dist, picker.SatisfiedHostIds)
		items = removeHostsFromItems(items, picker.SatisfiedHostIds)
	}
	if successCount != groupCount {
		t.Errorf("Expected all %d groups succeed, got %d (剩余库存=%d)",
			groupCount, successCount, len(items))
	}
}

// ------------------------------------------------------------------------
// Case 4：rack tolerance 触发切换 —— 大池子内 rack 集中度高导致 subzone 切换
// ------------------------------------------------------------------------
// bigzone 5 台机器全部挤在 rack-only-1 / rack-only-2 上 (rack 仅 2 个)
// 申请 4 台 WEAK → MaxPerRack=1，bigzone 最多取 2 台
// 期望：bigzone 取 2 台（被 rack tolerance 限制）、midzone 取 2 台
func TestWeakBigPool_RackToleranceForcesSwitch(t *testing.T) {
	baseTime := time.Now()
	items := []model.TbRpDetail{}
	hid := 20000
	for i := 0; i < 5; i++ { // bigzone 5 台 - 全部仅 2 个 rack
		hid++
		items = append(items, model.TbRpDetail{
			BkHostID: hid, IP: fmt.Sprintf("127.0.0.%d", hid-20000),
			AssetID: fmt.Sprintf("a-%d", hid), CityID: "city-1", City: "深圳",
			SubZone: "bigzone", SubZoneID: "bigzone",
			RackID: fmt.Sprintf("rack-only-%d", i%2+1),
			CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime,
		})
	}
	for i := 0; i < 5; i++ { // midzone 5 台 - 5 个 rack
		hid++
		items = append(items, model.TbRpDetail{
			BkHostID: hid, IP: fmt.Sprintf("127.0.0.%d", hid-20000),
			AssetID: fmt.Sprintf("a-%d", hid), CityID: "city-1", City: "深圳",
			SubZone: "midzone", SubZoneID: "midzone",
			RackID: fmt.Sprintf("rack-mz-%d", i+1),
			CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime,
		})
	}

	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 4, 0, nil)
	picker := createMockPickerObject(4)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("PickInstanceBase error: %v", err)
	}

	if got := len(picker.SatisfiedHostIds); got != 4 {
		t.Fatalf("Expected 4 hosts, got %d", got)
	}
	dist := countBySubzone(items, picker)
	t.Logf("分布: %v", dist)

	if dist["bigzone"] > 2 {
		t.Errorf("bigzone 不应超过 2 (rack=2, MaxPerRack=1), got %d", dist["bigzone"])
	}
	if dist["bigzone"] != 2 {
		t.Errorf("Expected bigzone=2 (取满两个 rack), got %d", dist["bigzone"])
	}
	if dist["midzone"] != 2 {
		t.Errorf("Expected midzone=2 (补足剩余), got %d", dist["midzone"])
	}
	logDistribution(t, items, picker, false)
	logPickedRacks(t, items, picker)
}

// ------------------------------------------------------------------------
// Case 5：库存不足 —— 算法应优雅退出，不死循环
// ------------------------------------------------------------------------
// 库存仅 2 台（1 subzone, 2 rack），申请 4 台 WEAK
// 期望：返回错误，picker 部分填充但不死循环
func TestWeakBigPool_InsufficientInventoryExitsGracefully(t *testing.T) {
	baseTime := time.Now()
	items := []model.TbRpDetail{
		{
			BkHostID: 30001, IP: "127.0.0.31", AssetID: "a31",
			CityID: "city-1", City: "深圳", SubZone: "only", SubZoneID: "only",
			RackID: "r1", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime,
		},
		{
			BkHostID: 30002, IP: "127.0.0.32", AssetID: "a32",
			CityID: "city-1", City: "深圳", SubZone: "only", SubZoneID: "only",
			RackID: "r2", CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime,
		},
	}

	ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, 4, 0, nil)
	picker := createMockPickerObject(4)
	done := make(chan struct{})
	go func() {
		_ = ctx.PickInstanceBase(picker, items)
		close(done)
	}()
	select {
	case <-done: // 正常退出
	case <-time.After(5 * time.Second):
		t.Fatal("pickerCrossSubzoneBigPoolFirst 死循环（超过 5s 未退出）")
	}

	// 库存只有 2 台，期望最多分到 2 台
	if got := len(picker.SatisfiedHostIds); got > 2 {
		t.Errorf("Expected at most 2 hosts, got %d", got)
	}
	t.Logf("分配数量: %d (符合库存上限 2)", len(picker.SatisfiedHostIds))
}

// ------------------------------------------------------------------------
// Case 6：STRONG 走旧 round-robin —— 验证调度分流正确，不影响 STRONG 行为
// ------------------------------------------------------------------------
// 库存：3 subzone 各 4 台，申请 3 台 STRONG（需 ≥3 subzone，每 subzone ≤1）
// 期望：3 个 subzone 各取 1 台（round-robin 平均分布）
func TestStrongStillUsesRoundRobin(t *testing.T) {
	baseTime := time.Now()
	items := []model.TbRpDetail{}
	hid := 40000
	zones := []string{"sz-a", "sz-b", "sz-c"}
	for _, sz := range zones {
		for i := 1; i <= 4; i++ {
			hid++
			items = append(items, model.TbRpDetail{
				BkHostID: hid, IP: fmt.Sprintf("127.0.0.%d", hid-40000),
				AssetID: fmt.Sprintf("a-%d", hid), CityID: "city-1", City: "深圳",
				SubZone: sz, SubZoneID: sz,
				RackID: fmt.Sprintf("%s-rack-%d", sz, i),
				CPUNum: 16, DramCap: 64, Status: "Unused", CreateTime: baseTime,
			})
		}
	}

	ctx := createMockSearchContext(CROSS_SUBZONE_STRONG, 3, 0, nil)
	picker := createMockPickerObject(3)
	if err := ctx.PickInstanceBase(picker, items); err != nil {
		t.Fatalf("PickInstanceBase error: %v", err)
	}
	if got := len(picker.SatisfiedHostIds); got != 3 {
		t.Fatalf("Expected 3 hosts, got %d", got)
	}
	dist := countBySubzone(items, picker)
	if len(dist) != 3 {
		t.Errorf("Expected 3 distinct subzones (STRONG round-robin), got %d (dist=%v)",
			len(dist), dist)
	}
	for sz, n := range dist {
		if n != 1 {
			t.Errorf("Expected each subzone has exactly 1 host, %s got %d", sz, n)
		}
	}
	logDistribution(t, items, picker, false)
}

// ------------------------------------------------------------------------
// Case 7：真实生产场景 —— 30 组 × 3 台 WEAK，南京机房 119 台库存
// ------------------------------------------------------------------------
// 数据来源：生产库 tb_rp_detail（city 已统一归一为"南京"，机型统一为 16C/64G）
//
// 库存分布（53 个 rack，共 119 台）：
//   - 南京-吉山 (nanjing-jishan)        : 62 台 / 27 rack
//   - 南京-吴越 (nanjing-wuyue)         : 27 台 /  3 rack（含一个 18 台的大 rack）
//   - 仪征-东升 (yizheng-dongsheng)     : 23 台 / 16 rack
//   - 南京-学府 (nanjing-xuefu)         :  4 台 /  4 rack
//   - 南京-江宁 (nanjing-jiangning)     :  2 台 /  2 rack
//   - 南京-长安 (nanjing-changan)       :  1 台 /  1 rack
//
// 关键约束（n=3 → MaxPerSubZone=2, MaxPerRack=1）：
//   - 每组每 subzone 最多 2 台
//   - 每组每 rack 最多 1 台
//
// 总需求 90 台 ≤ 总库存 119 台，理论上库存充足。
// 旧 round-robin 算法在该场景下因小池子（长安/江宁/学府）反复被均衡消耗到归零，
// 导致后续多组 WEAK 失败；两阶段算法验证 30 组全成功率。
func TestWeakBigPool_RealScenario_NanjingProduction_30Groups(t *testing.T) {
	type rackInv struct {
		subzoneCN string // 中文显示名
		subzoneID string // 算法用的 ID
		rackID    string
		count     int
	}
	rackData := []rackInv{
		// cnt=1（28 个 rack）
		{"仪征-东升", "yizheng-dongsheng", "590332", 1},
		{"南京-吉山", "nanjing-jishan", "469011", 1},
		{"仪征-东升", "yizheng-dongsheng", "655906", 1},
		{"南京-学府", "nanjing-xuefu", "400543", 1},
		{"南京-吉山", "nanjing-jishan", "469701", 1},
		{"南京-江宁", "nanjing-jiangning", "786767", 1},
		{"南京-吉山", "nanjing-jishan", "528075", 1},
		{"仪征-东升", "yizheng-dongsheng", "547831", 1},
		{"南京-吉山", "nanjing-jishan", "467319", 1},
		{"南京-吉山", "nanjing-jishan", "469033", 1},
		{"南京-长安", "nanjing-changan", "848502", 1},
		{"仪征-东升", "yizheng-dongsheng", "591104", 1},
		{"南京-吉山", "nanjing-jishan", "527945", 1},
		{"南京-学府", "nanjing-xuefu", "397581", 1},
		{"南京-吉山", "nanjing-jishan", "468413", 1},
		{"仪征-东升", "yizheng-dongsheng", "769046", 1},
		{"南京-江宁", "nanjing-jiangning", "791370", 1},
		{"仪征-东升", "yizheng-dongsheng", "656380", 1},
		{"南京-学府", "nanjing-xuefu", "619818", 1},
		{"南京-吉山", "nanjing-jishan", "528267", 1},
		{"仪征-东升", "yizheng-dongsheng", "590641", 1},
		{"仪征-东升", "yizheng-dongsheng", "590894", 1},
		{"南京-吉山", "nanjing-jishan", "469137", 1},
		{"仪征-东升", "yizheng-dongsheng", "656053", 1},
		{"仪征-东升", "yizheng-dongsheng", "590739", 1},
		{"仪征-东升", "yizheng-dongsheng", "656574", 1},
		{"南京-学府", "nanjing-xuefu", "617775", 1},
		{"南京-吉山", "nanjing-jishan", "528335", 1},
		// cnt=2（12 个 rack）
		{"南京-吉山", "nanjing-jishan", "469207", 2},
		{"仪征-东升", "yizheng-dongsheng", "590245", 2},
		{"南京-吉山", "nanjing-jishan", "468343", 2},
		{"南京-吉山", "nanjing-jishan", "467465", 2},
		{"仪征-东升", "yizheng-dongsheng", "656665", 2},
		{"南京-吉山", "nanjing-jishan", "391479", 2},
		{"仪征-东升", "yizheng-dongsheng", "590536", 2},
		{"南京-吉山", "nanjing-jishan", "469519", 2},
		{"南京-吉山", "nanjing-jishan", "467795", 2},
		{"南京-吉山", "nanjing-jishan", "469543", 2},
		{"南京-吉山", "nanjing-jishan", "467837", 2},
		{"南京-吉山", "nanjing-jishan", "393585", 2},
		// cnt=3（7 个 rack）
		{"南京-吉山", "nanjing-jishan", "469957", 3},
		{"仪征-东升", "yizheng-dongsheng", "548791", 3},
		{"南京-吉山", "nanjing-jishan", "469559", 3},
		{"南京-吉山", "nanjing-jishan", "469197", 3},
		{"仪征-东升", "yizheng-dongsheng", "590884", 3},
		{"南京-吉山", "nanjing-jishan", "391179", 3},
		{"南京-吉山", "nanjing-jishan", "469535", 3},
		// cnt=4（2 个 rack）
		{"南京-吴越", "nanjing-wuyue", "854229", 4},
		{"南京-吉山", "nanjing-jishan", "468157", 4},
		// cnt=5（1 个 rack）
		{"南京-吴越", "nanjing-wuyue", "854546", 5},
		// cnt=7（1 个 rack）
		{"南京-吉山", "nanjing-jishan", "393931", 7},
		// cnt=8（1 个 rack）
		{"南京-吉山", "nanjing-jishan", "469071", 8},
		// cnt=18（1 个 rack，最大单 rack）
		{"南京-吴越", "nanjing-wuyue", "854488", 18},
	}

	baseTime := time.Now()
	items := make([]model.TbRpDetail, 0, 119)
	hid := 50000
	for _, r := range rackData {
		for i := 0; i < r.count; i++ {
			hid++
			items = append(items, model.TbRpDetail{
				BkHostID:    hid,
				IP:          fmt.Sprintf("127.0.0.%d", (hid-50000)%255+1),
				AssetID:     fmt.Sprintf("a-%d", hid),
				CityID:      "nanjing",
				City:        "南京",
				SubZone:     r.subzoneCN,
				SubZoneID:   r.subzoneID,
				RackID:      r.rackID,
				NetDeviceID: fmt.Sprintf("switch-%s", r.rackID),
				CPUNum:      16,
				DramCap:     64,
				Status:      "Unused",
				CreateTime:  baseTime,
			})
		}
	}

	// 初始库存日志
	initInv := make(map[string]int)
	for _, it := range items {
		initInv[it.SubZoneID]++
	}
	t.Logf("=== 初始库存（共 %d 台）===", len(items))
	for sz, n := range initInv {
		t.Logf("  %-25s : %d 台", sz, n)
	}

	const groupCount = 30
	const perGroup = 3

	// 收集每组分配结果，循环内不打印，最后统一输出
	type groupResult struct {
		groupID  int
		success  bool
		errMsg   string
		hosts    []model.TbRpDetail // 分配到的机器明细（按 picker.SatisfiedHostIds 顺序）
		distZone map[string]int     // 该组的 subzone 分布
		distRack map[string]int     // 该组的 rack 分布
	}
	results := make([]groupResult, 0, groupCount)
	successCount := 0
	totalAllocated := 0
	subzoneCumulative := make(map[string]int)
	rackCumulative := make(map[string]int) // 跨组的 rack 累计使用次数
	failedGroups := []int{}

	for g := 1; g <= groupCount; g++ {
		ctx := createMockSearchContext(CROSS_SUBZONE_WEAK, perGroup, 0, nil)
		picker := createMockPickerObject(perGroup)
		err := ctx.PickInstanceBase(picker, items)
		res := groupResult{groupID: g, distZone: map[string]int{}, distRack: map[string]int{}}
		if err != nil {
			res.errMsg = fmt.Sprintf("%v (剩余库存:%d)", err, len(items))
			failedGroups = append(failedGroups, g)
			results = append(results, res)
			continue
		}
		if len(picker.SatisfiedHostIds) != perGroup {
			res.errMsg = fmt.Sprintf("got %d/%d hosts (剩余库存:%d)",
				len(picker.SatisfiedHostIds), perGroup, len(items))
			failedGroups = append(failedGroups, g)
			results = append(results, res)
			continue
		}
		// 索引当前 items（在 remove 之前）
		idx := make(map[int]model.TbRpDetail, len(items))
		for _, it := range items {
			idx[it.BkHostID] = it
		}
		for _, hid := range picker.SatisfiedHostIds {
			if it, ok := idx[hid]; ok {
				res.hosts = append(res.hosts, it)
				res.distZone[it.SubZoneID]++
				res.distRack[it.RackID]++
				subzoneCumulative[it.SubZoneID]++
				rackCumulative[it.RackID]++
			}
		}
		res.success = true
		successCount++
		totalAllocated += perGroup
		results = append(results, res)
		items = removeHostsFromItems(items, picker.SatisfiedHostIds)
	}

	// ============= 统一输出 =============
	t.Logf("==================== 每组分配明细 ====================")
	for _, r := range results {
		if !r.success {
			t.Logf("group %2d FAIL: %s", r.groupID, r.errMsg)
			continue
		}
		t.Logf("group %2d OK,  zone_dist=%v  rack_dist=%v", r.groupID, r.distZone, r.distRack)
		for i, it := range r.hosts {
			t.Logf("           [%d] host_id=%d  ip=%-15s  subzone=%-20s  rack=%s",
				i+1, it.BkHostID, it.IP, it.SubZoneID, it.RackID)
		}
	}

	t.Logf("==================== 汇总 ====================")
	t.Logf("成功 %d/%d 组, 共分配 %d 台", successCount, groupCount, totalAllocated)
	if len(failedGroups) > 0 {
		t.Logf("失败组: %v", failedGroups)
	}
	t.Logf("--- 各 subzone 累计消耗 ---")
	for sz, n := range subzoneCumulative {
		t.Logf("  %-25s : %d 台 (剩余 %d)", sz, n, initInv[sz]-n)
	}
	t.Logf("--- 各 rack_id 累计使用次数（仅显示被使用过的 rack） ---")
	// rack 按使用次数降序输出，便于一眼看到"热门"rack
	type rackStat struct {
		rackID string
		count  int
	}
	rackStats := make([]rackStat, 0, len(rackCumulative))
	for r, n := range rackCumulative {
		rackStats = append(rackStats, rackStat{r, n})
	}
	sort.Slice(rackStats, func(i, j int) bool {
		if rackStats[i].count != rackStats[j].count {
			return rackStats[i].count > rackStats[j].count
		}
		return rackStats[i].rackID < rackStats[j].rackID
	})
	for _, rs := range rackStats {
		t.Logf("  rack=%-8s : %d 次", rs.rackID, rs.count)
	}
	t.Logf("总剩余库存: %d 台 (被使用过的 rack 数: %d)", len(items), len(rackCumulative))

	if successCount != groupCount {
		t.Errorf("Expected all %d groups succeed (resources sufficient), got %d (failed groups: %v)",
			groupCount, successCount, failedGroups)
	}
}
