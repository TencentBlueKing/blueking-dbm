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
	"math"
	"slices"
	"sort"
	"strings"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	mapset "github.com/deckarep/golang-set/v2"
	"github.com/patrickmn/go-cache"
	"github.com/samber/lo"
)

const (
	// MINDISTRUTE TODO
	MINDISTRUTE = 20
	// RANDOM TODO
	RANDOM = "RANDOM"
)

type subZone = string

// PickerObject picker object
type PickerObject struct {
	Item           string
	Count          int
	PickDistribute map[string]int
	// 已存在的园区
	ExistSubZone        []subZone
	SatisfiedHostIds    []int
	SatisfiedHostIdsMap map[subZone][]int
	// SelectedResources []*model.TbRpDetail
	// 待选择实例
	// 具备优先级的待选实例列表
	PriorityElements      map[subZone]*PriorityQueue
	SubZonePrioritySumMap map[subZone]int64

	// 资源请求在同园区的时候才生效
	// 已存在的机架ID
	ExistRackIds []string
	// 已存在的网卡ID
	ExistLinkNetdeviceIds []string
	// 处理日志
	ProcessLogs []string

	// 容忍度相关字段 - 用于CROS_SUBZONE亲和性
	Tolerance             float64         // 容忍度参数
	CurrentHostsBySubZone map[subZone]int // 当前集群已存在资源按园区分组的数量
	TotalCount            int             // 总数量（申请数量 + 当前已存在数量）
	MaxPerSubZone         int             // 每个园区最大容忍机器数量

	// 机架级别容忍度相关字段 - 用于SAME_SUBZONE跨机架亲和性
	CurrentHostsByRack map[string]int // 当前集群已存在资源按机架分组的数量
	MaxPerRack         int            // 每个机架最大容忍机器数量
	RackDistribute     map[string]int // 当前分配中各机架的机器数量
}

// LockReturnPickers 将匹配好的机器资源,查询出详情结果返回
//
//	@param elements
//	@return []model.BatchGetTbDetailResult
//	@return error
func LockReturnPickers(elements []*PickerObject, mode string) ([]model.BatchGetTbDetailResult, error) {
	var getter []model.BatchGetTbDetail
	for _, v := range elements {
		getter = append(getter, model.BatchGetTbDetail{
			Item:      v.Item,
			BkHostIds: v.SatisfiedHostIds,
		})
	}
	data, err := model.BatchGetSatisfiedByAssetIds(getter, mode)
	if err != nil {
		logger.Error(fmt.Sprintf("占用机器，更改机器状态失败%s", err.Error()))
	}
	if mode == model.Used {
		sendArchivedTask(data)
	}

	// 构建分配结果的汇总信息（Summary）
	// 非机架级（跨园区等）：按 城市 -> subzone 聚合数量
	// 机架级（同园区、跨交换机等）：按 subzone -> rack_id 聚合数量
	itemToPicker := make(map[string]*PickerObject)
	for _, p := range elements {
		itemToPicker[p.Item] = p
	}

	for i := range data {
		res := &data[i]
		picker, ok := itemToPicker[res.Item]
		if !ok {
			continue
		}

		if picker.MaxPerRack > 0 { // 机架级聚合
			bySubZoneRack := make(map[string]map[string]int)
			for _, d := range res.Data {
				sz := d.SubZoneID
				r := d.RackID
				if _, exists := bySubZoneRack[sz]; !exists {
					bySubZoneRack[sz] = make(map[string]int)
				}
				bySubZoneRack[sz][r]++
			}
			if res.Summary == nil {
				res.Summary = make(map[string]interface{})
			}
			res.Summary["by_subzone_rack"] = bySubZoneRack
		} else { // 园区级聚合
			byCitySubZone := make(map[string]map[string]int)
			for _, d := range res.Data {
				city := d.City
				sz := d.SubZoneID
				if _, exists := byCitySubZone[city]; !exists {
					byCitySubZone[city] = make(map[string]int)
				}
				byCitySubZone[city][sz]++
			}
			if res.Summary == nil {
				res.Summary = make(map[string]interface{})
			}
			res.Summary["by_city_subzone"] = byCitySubZone
		}
	}

	return data, err
}

// sendArchivedTask 归档
//
//	@param data
func sendArchivedTask(data []model.BatchGetTbDetailResult) {
	for _, v := range data {
		for _, l := range v.Data {
			task.ArchivedResourceChan <- l.ID
		}
	}
}

// createNice 创建Nice值
//
//	@param cpu
//	@param mem
//	@param sdd
//	@param hdd
//	@return rs
func createNice(cpu int, mem, sdd, hdd int) (rs int64) {
	rs = int64(cpu*1000000000000 + mem*100000 + sdd + hdd)
	return
}

// AnalysisResource 待选取资源排序
//
//	@param ins
//	@return map
func AnalysisResource(ins []model.TbRpDetail, israndom bool) map[string][]InstanceObject {
	result := make(map[string][]InstanceObject)
	for _, v := range ins {
		linkids := strings.Split(v.NetDeviceID, ",")
		t := InstanceObject{
			BkHostId:        v.BkHostID,
			RackId:          v.RackID,
			LinkNetdeviceId: linkids,
			Nice:            createNice(int(v.CPUNum), v.DramCap, 0, 0),
			InsDetail:       &v,
		}
		if israndom {
			result[RANDOM] = append(result[RANDOM], t)
		} else {
			result[v.SubZone] = append(result[v.SubZone], t)
		}
	}

	// 对个每个camp里面机器按照规则排序，便于后续picker的时候取最优的
	for key := range result {
		sort.Sort(Wrapper{result[key], func(p, q *InstanceObject) bool {
			return q.Nice > p.Nice // Nice 递减排序
		}})
	}
	return result
}

// NewPicker 初始化资源选择器
//
//	@param count
//	@param item
//	@return *PickerObject
func NewPicker(count int, item string) *PickerObject {
	return &PickerObject{
		Item:                  item,
		Count:                 count,
		ExistRackIds:          make([]string, 0),
		ExistLinkNetdeviceIds: make([]string, 0),
		SatisfiedHostIds:      make([]int, 0),
		SatisfiedHostIdsMap:   make(map[subZone][]int),
		PickDistribute:        make(map[string]int),
		CurrentHostsBySubZone: make(map[subZone]int),
		CurrentHostsByRack:    make(map[string]int),
		RackDistribute:        make(map[string]int),
		Tolerance:             -1, // 默认值-1表示未设置容忍度
		MaxPerSubZone:         0,
		MaxPerRack:            0,
		TotalCount:            count,
	}
}

// CrossSwitchCheck 跨交换机检查
func (c *PickerObject) CrossSwitchCheck(v InstanceObject) bool {
	if len(v.LinkNetdeviceId) == 0 {
		return false
	}
	return c.InterSectForLinkNetDevice(v.LinkNetdeviceId) == 0
}

// CrossRackCheck 跨机架检查
func (c *PickerObject) CrossRackCheck(v InstanceObject) bool {
	if cmutil.IsEmpty(v.RackId) {
		return false
	}
	return c.InterSectForEquipment(v.RackId) == 0
}

// DebugDistributeLog debug log
func (c *PickerObject) DebugDistributeLog() {
	for key, v := range c.PickDistribute {
		logger.Debug(fmt.Sprintf("Zone:%s,PickCount:%d", key, v))
	}
}

// PreselectedSatisfiedInstance preselect satisfied resource
func (c *PickerObject) PreselectedSatisfiedInstance() error {
	affectRows, err := model.UpdateTbRpDetail(c.SatisfiedHostIds, model.Preselected)
	if err != nil {
		return err
	}
	if int(affectRows) != len(c.SatisfiedHostIds) {
		return fmt.Errorf("update %d qualified resource to preselect,only %d real update status", len(c.SatisfiedHostIds),
			affectRows)
	}
	return nil
}

// RollbackUnusedInstance roll back unselected resources
func (c *PickerObject) RollbackUnusedInstance() error {
	return model.UpdateTbRpDetailStatusAtSelling(c.SatisfiedHostIds, model.Unused)
}

// CampusNice build campus
type CampusNice struct {
	Campus string `json:"campus"`
	Count  int64  `json:"count"`
}

// CampusWrapper 园区排序
type CampusWrapper struct {
	Campus []CampusNice
	by     func(p, q *CampusNice) bool
}

// Len 用于排序
func (pw CampusWrapper) Len() int {
	return len(pw.Campus)
}

// Swap 用于排序
func (pw CampusWrapper) Swap(i, j int) {
	pw.Campus[i], pw.Campus[j] = pw.Campus[j], pw.Campus[i]
}

// Less 用于排序
func (pw CampusWrapper) Less(i, j int) bool {
	return pw.by(&pw.Campus[i], &pw.Campus[j])
}

// PickerDone picker done
func (c *PickerObject) PickerDone() bool {
	return len(c.SatisfiedHostIds) == c.Count
}

// InterSectForEquipment 求交集 EquipmentID
func (c *PickerObject) InterSectForEquipment(equipmentId string) int {
	baseSet := mapset.NewSet[string]()
	for _, v := range cmutil.RemoveDuplicate(c.ExistRackIds) {
		baseSet.Add(v)
	}
	myset := mapset.NewSet[string]()
	myset.Add(equipmentId)
	return baseSet.Intersect(myset).Cardinality()
}

// InterSectForLinkNetDevice 求交集 LinkNetDeviceIds
func (c *PickerObject) InterSectForLinkNetDevice(linkDeviceIds []string) int {
	baseSet := mapset.NewSet[string]()
	for _, v := range cmutil.RemoveDuplicate(c.ExistLinkNetdeviceIds) {
		baseSet.Add(v)
	}
	myset := mapset.NewSet[string]()
	for _, linkId := range linkDeviceIds {
		if cmutil.IsNotEmpty(linkId) {
			myset.Add(linkId)
		}
	}
	return baseSet.Intersect(myset).Cardinality()
}

// InstanceObject instance object
type InstanceObject struct {
	BkHostId        int
	RackId          string
	LinkNetdeviceId []string
	Nice            int64
	InsDetail       *model.TbRpDetail
}

// GetLinkNetDeviceIdsInterface getLinkNetDeviceIdsInterface
func (c *InstanceObject) GetLinkNetDeviceIdsInterface() []interface{} {
	var k []interface{}
	for _, v := range c.LinkNetdeviceId {
		k = append(k, v)
	}
	return k
}

// Wrapper Wrapper
type Wrapper struct {
	Instances []InstanceObject
	by        func(p, q *InstanceObject) bool
}

// SortBy sort by
type SortBy func(p, q *InstanceObject) bool

// Len 用于排序
func (pw Wrapper) Len() int { // 重写 Len() 方法
	return len(pw.Instances)
}

// Swap 用于排序
func (pw Wrapper) Swap(i, j int) { // 重写 Swap() 方法
	pw.Instances[i], pw.Instances[j] = pw.Instances[j], pw.Instances[i]
}

// Less 用于排序
func (pw Wrapper) Less(i, j int) bool { // 重写 Less() 方法
	return pw.by(&pw.Instances[i], &pw.Instances[j])
}

// InitToleranceConfig 初始化容忍度相关配置
func (c *PickerObject) InitToleranceConfig(tolerance float64, currentHosts []CurrentResource, requestCount int) {
	c.Tolerance = tolerance
	c.CurrentHostsBySubZone = make(map[subZone]int)

	// 统计当前主机在各个园区的分布
	for _, host := range currentHosts {
		c.CurrentHostsBySubZone[host.SubZone]++
	}

	// 计算总数量
	currentTotalCount := len(currentHosts)
	c.TotalCount = currentTotalCount + requestCount

	// 计算每个园区最大容忍机器数量
	if tolerance == 0 {
		// tolerance为0表示必须跨园区，每个园区最多只能有1台机器
		c.MaxPerSubZone = 1
	} else {
		// 使用向上取整计算每个园区最大容忍数量
		c.MaxPerSubZone = int(math.Ceil(float64(c.TotalCount) * tolerance))
	}

	logger.Info("园区级容忍度配置: tolerance=%.2f, totalCount=%d, maxPerSubZone=%d, currentHosts=%v",
		tolerance, c.TotalCount, c.MaxPerSubZone, c.CurrentHostsBySubZone)
}

// InitRackToleranceConfig 初始化机架级别的容忍度相关配置
func (c *PickerObject) InitRackToleranceConfig(tolerance float64, currentHosts []CurrentResource, requestCount int) {
	c.Tolerance = tolerance
	c.CurrentHostsByRack = make(map[string]int)
	c.RackDistribute = make(map[string]int)

	// 统计当前主机在各个机架的分布
	for _, host := range currentHosts {
		if host.RackId != "" {
			c.CurrentHostsByRack[host.RackId]++
		}
	}

	// 计算总数量
	currentTotalCount := len(currentHosts)
	c.TotalCount = currentTotalCount + requestCount

	// 计算每个机架最大容忍机器数量
	if tolerance == 0 {
		// tolerance为0表示必须跨机架，每个机架最多只能有1台机器
		c.MaxPerRack = 1
	} else {
		// 使用向上取整计算每个机架最大容忍数量
		c.MaxPerRack = int(math.Ceil(float64(c.TotalCount) * tolerance))
	}

	logger.Info("机架级容忍度配置: tolerance=%.2f, totalCount=%d, maxPerRack=%d, currentRackHosts=%v",
		tolerance, c.TotalCount, c.MaxPerRack, c.CurrentHostsByRack)
}

// CanAllocateToSubZone 检查是否可以向指定园区分配机器
func (c *PickerObject) CanAllocateToSubZone(subZone string) bool {
	if c.Tolerance == 0 {
		// tolerance为0时，必须跨园区，检查该园区是否已经有机器
		currentCount := c.CurrentHostsBySubZone[subZone]
		allocatedCount := c.PickDistribute[subZone]
		return currentCount+allocatedCount == 0
	}

	// 检查该园区当前总数是否超过容忍限制
	currentCount := c.CurrentHostsBySubZone[subZone]
	allocatedCount := c.PickDistribute[subZone]
	totalInSubZone := currentCount + allocatedCount

	return totalInSubZone < c.MaxPerSubZone
}

// GetSubZoneCurrentTotal 获取指定园区当前总机器数（包括已存在的和已分配的）
func (c *PickerObject) GetSubZoneCurrentTotal(subZone string) int {
	currentCount := c.CurrentHostsBySubZone[subZone]
	allocatedCount := c.PickDistribute[subZone]
	return currentCount + allocatedCount
}

// CanAllocateToRack 检查是否可以向指定机架分配机器
func (c *PickerObject) CanAllocateToRack(rackId string) bool {
	if c.Tolerance == 0 {
		// tolerance为0时，必须跨机架，检查该机架是否已经有机器
		currentCount := c.CurrentHostsByRack[rackId]
		allocatedCount := c.RackDistribute[rackId]
		return currentCount+allocatedCount == 0
	}

	// 检查该机架当前总数是否超过容忍限制
	currentCount := c.CurrentHostsByRack[rackId]
	allocatedCount := c.RackDistribute[rackId]
	totalInRack := currentCount + allocatedCount

	return totalInRack < c.MaxPerRack
}

// GetRackCurrentTotal 获取指定机架当前总机器数（包括已存在的和已分配的）
func (c *PickerObject) GetRackCurrentTotal(rackId string) int {
	currentCount := c.CurrentHostsByRack[rackId]
	allocatedCount := c.RackDistribute[rackId]
	return currentCount + allocatedCount
}

// SortSubZoneByBalance 按照均衡原则（按当前机器数）排序园区
// 优先选择当前机器数量较少的园区，在容忍度限制内实现均衡分配
func (c *PickerObject) SortSubZoneByBalance(cross_subzone bool) []string {
	type subZoneBalance struct {
		subZone      string
		currentTotal int     // 当前机器总数（已存在 + 已分配）
		capacity     int     // 可用容量
		priority     int64   // 资源优先级
		balanceScore float64 // 均衡得分（越小越优先）
	}

	var candidates []subZoneBalance

	for subZone, pq := range c.PriorityElements {
		if pq == nil || pq.Len() == 0 {
			continue
		}

		// 检查是否可以分配到该园区
		if c.Tolerance >= 0 && c.MaxPerSubZone > 0 {
			if !c.CanAllocateToSubZone(subZone) {
				continue
			}
		}

		currentTotal := c.GetSubZoneCurrentTotal(subZone)
		capacity := pq.Len()

		// 获取园区优先级
		var priority int64
		if v, ok := c.SubZonePrioritySumMap[subZone]; ok {
			priority = v
		}

		// 计算均衡得分：当前机器数越低，得分越低（优先级越高）
		// 同时考虑资源可用性和优先级
		balanceScore := float64(currentTotal)

		// 如果设置了容忍度，优先考虑均衡
		if c.Tolerance > 0 && c.MaxPerSubZone > 0 {
			// 相对占用率：当前总数 / 最大容忍数
			loadRatio := float64(currentTotal) / float64(c.MaxPerSubZone)
			balanceScore = loadRatio * 100 // 放大以便排序
		} else if c.Tolerance == 0 {
			// tolerance=0时，优先选择没有机器的园区
			if currentTotal > 0 {
				continue // 跳过已有机器的园区
			}
			balanceScore = 0
		}

		// 资源越多的园区，在同等占用下优先级稍高
		balanceScore -= float64(capacity) * 0.001

		// 优先级越高的园区，在同等占用下优先级稍高
		balanceScore -= float64(priority) * 0.000001

		candidates = append(candidates, subZoneBalance{
			subZone:      subZone,
			currentTotal: currentTotal,
			capacity:     capacity,
			priority:     priority,
			balanceScore: balanceScore,
		})
	}

	// 按照均衡得分排序，得分低的优先
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].balanceScore < candidates[j].balanceScore
	})

	// 提取园区名称
	result := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		result = append(result, candidate.subZone)
		remainingCapacity := candidate.capacity - candidate.currentTotal
		logger.Debug("园区 %s: 当前机器数=%d, 容量=%d, 剩余可用=%d, 均衡得分=%.3f",
			candidate.subZone, candidate.currentTotal, candidate.capacity, remainingCapacity, candidate.balanceScore)
	}

	// 输出排序后的园区及其剩余可用数量
	var resultWithCapacity []string
	for _, candidate := range candidates {
		remainingCapacity := candidate.capacity - candidate.currentTotal
		resultWithCapacity = append(resultWithCapacity, fmt.Sprintf("%s(剩余:%d)", candidate.subZone, remainingCapacity))
	}
	logger.Info("均衡排序后的园区顺序: %v", resultWithCapacity)
	return result
}

// SortRackByBalance 按照均衡原则（按当前机器数）排序机架
// 优先选择当前机器数量较少的机架，在容忍度限制内实现均衡分配
func (c *PickerObject) SortRackByBalance(subZone string) []string {
	type rackBalance struct {
		rackId       string
		currentTotal int     // 当前机器总数（已存在 + 已分配）
		capacity     int     // 可用容量
		priority     int64   // 资源优先级
		balanceScore float64 // 均衡得分（越小越优先）
	}

	var candidates []rackBalance

	// 统计该园区下所有机架的资源
	rackResources := make(map[string]int)
	rackPriorities := make(map[string]int64)

	if pq, ok := c.PriorityElements[subZone]; ok && pq != nil {
		// 临时复制队列内容进行统计
		tempItems := make([]*Item, 0, pq.Len())
		for pq.Len() > 0 {
			item, _ := pq.Pop()
			tempItems = append(tempItems, item)

			if v, ok := item.Value.(InstanceObject); ok {
				rackResources[v.RackId]++
				rackPriorities[v.RackId] += item.Priority
			}
		}

		// 恢复队列
		for _, item := range tempItems {
			if err := pq.Push(item); err != nil {
				logger.Error("failed to push item back to queue: %v", err)
			}
		}
	}

	for rackId, capacity := range rackResources {
		if capacity == 0 {
			continue
		}

		// 检查是否可以分配到该机架
		if c.Tolerance >= 0 && c.MaxPerRack > 0 {
			if !c.CanAllocateToRack(rackId) {
				continue
			}
		}

		currentTotal := c.GetRackCurrentTotal(rackId)
		priority := rackPriorities[rackId]

		// 计算均衡得分：当前机器数越低，得分越低（优先级越高）
		balanceScore := float64(currentTotal)

		// 如果设置了容忍度，优先考虑均衡
		if c.Tolerance > 0 && c.MaxPerRack > 0 {
			// 相对占用率：当前总数 / 最大容忍数
			loadRatio := float64(currentTotal) / float64(c.MaxPerRack)
			balanceScore = loadRatio * 100 // 放大以便排序
		} else if c.Tolerance == 0 {
			// tolerance=0时，优先选择没有机器的机架
			if currentTotal > 0 {
				continue // 跳过已有机器的机架
			}
			balanceScore = 0
		}

		// 资源越多的机架，在同等占用下优先级稍高
		balanceScore -= float64(capacity) * 0.001

		// 优先级越高的机架，在同等占用下优先级稍高
		balanceScore -= float64(priority) * 0.000001

		candidates = append(candidates, rackBalance{
			rackId:       rackId,
			currentTotal: currentTotal,
			capacity:     capacity,
			priority:     priority,
			balanceScore: balanceScore,
		})
	}

	// 按照均衡得分排序，得分低的优先
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].balanceScore < candidates[j].balanceScore
	})

	// 提取机架ID
	result := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		result = append(result, candidate.rackId)
		logger.Debug("机架 %s: 当前机器数=%d, 容量=%d, 均衡得分=%.3f",
			candidate.rackId, candidate.currentTotal, candidate.capacity, candidate.balanceScore)
	}

	logger.Info("均衡排序后的机架顺序 (园区%s): %v", subZone, result)
	return result
}

// GetCurrentDistributionInfo 获取当前分配情况的统计信息
func (c *PickerObject) GetCurrentDistributionInfo() map[string]interface{} {
	info := make(map[string]interface{})

	// 总体统计
	info["total_requested"] = c.Count
	info["total_allocated"] = len(c.SatisfiedHostIds)
	totalExisting := 0
	for _, count := range c.CurrentHostsBySubZone {
		totalExisting += count
	}
	info["total_existing"] = totalExisting

	// 园区分布统计
	distribution := make(map[string]map[string]int)
	allSubZones := make(map[string]bool)

	// 收集所有园区
	for subZone := range c.CurrentHostsBySubZone {
		allSubZones[subZone] = true
	}
	for subZone := range c.PickDistribute {
		allSubZones[subZone] = true
	}

	// 统计每个园区的详细信息
	for subZone := range allSubZones {
		distribution[subZone] = map[string]int{
			"existing":  c.CurrentHostsBySubZone[subZone],
			"allocated": c.PickDistribute[subZone],
			"total":     c.GetSubZoneCurrentTotal(subZone),
		}
		if c.MaxPerSubZone > 0 {
			distribution[subZone]["max_allowed"] = c.MaxPerSubZone
			distribution[subZone]["remaining"] = c.MaxPerSubZone - c.GetSubZoneCurrentTotal(subZone)
		}
	}

	info["distribution"] = distribution
	info["tolerance"] = c.Tolerance
	info["max_per_subzone"] = c.MaxPerSubZone

	return info
}

// CalculateBalanceScore 计算当前分配的均衡得分
// 返回值越小表示分布越均衡
func (c *PickerObject) CalculateBalanceScore() float64 {
	if len(c.PickDistribute) <= 1 {
		return 0 // 只有一个园区或没有分配，认为是完全均衡的
	}

	var loads []int
	totalLoad := 0

	// 收集所有园区的负载
	allSubZones := make(map[string]bool)
	for subZone := range c.CurrentHostsBySubZone {
		allSubZones[subZone] = true
	}
	for subZone := range c.PickDistribute {
		allSubZones[subZone] = true
	}

	for subZone := range allSubZones {
		load := c.GetSubZoneCurrentTotal(subZone)
		loads = append(loads, load)
		totalLoad += load
	}

	if len(loads) == 0 || totalLoad == 0 {
		return 0
	}

	// 计算平均负载
	avgLoad := float64(totalLoad) / float64(len(loads))

	// 计算标准差作为均衡得分
	var variance float64
	for _, load := range loads {
		diff := float64(load) - avgLoad
		variance += diff * diff
	}

	variance /= float64(len(loads))
	standardDeviation := math.Sqrt(variance)

	// 标准化得分：标准差 / 平均负载，避免除零
	if avgLoad == 0 {
		return standardDeviation
	}

	return standardDeviation / avgLoad
}

// ShouldRebalance 判断是否需要重新平衡
func (c *PickerObject) ShouldRebalance() bool {
	// 如果没有设置容忍度，或者分配的机器数量较少，不需要重新平衡
	if c.Tolerance < 0 || len(c.SatisfiedHostIds) < 3 {
		return false
	}

	balanceScore := c.CalculateBalanceScore()

	// 如果均衡得分超过阈值，建议重新平衡
	// 阈值可以根据实际需求调整
	threshold := 0.3
	if c.Tolerance == 0 {
		// tolerance=0时，要求更严格的均衡
		threshold = 0.1
	}

	shouldRebalance := balanceScore > threshold
	if shouldRebalance {
		logger.Info("当前均衡得分 %.3f 超过阈值 %.3f，建议重新平衡", balanceScore, threshold)
	}

	return shouldRebalance
}

// GlobalBalanceCoordinator 全局均衡分配协调器
type GlobalBalanceCoordinator struct {
	RequestParam      RequestInputParam
	GlobalDistribute  map[string]int                // 全局园区/机架分配统计
	GlobalRackDistrib map[string]int                // 全局机架分配统计
	TotalRequestCount int                           // 总请求数量
	AllAffinities     []string                      // 所有亲和性类型
	GlobalTolerance   float64                       // 全局容忍度
	IsRackLevel       bool                          // 是否是机架级别的分配
	MaxPerUnit        int                           // 每个单元(园区/机架)最大容忍数量
	CurrentUnitCounts map[string]int                // 当前单元已存在的机器数量
	RequestContexts   []*SearchContext              // 所有请求上下文
	AllResourcePools  map[string][]model.TbRpDetail // 所有可用资源池 key=subzone

	// 城市观测数据（仅用于日志/容量预估，不参与硬过滤）
	CityTolerance    map[string]float64 // 每城市平均容忍度（观测）
	CityMaxPerUnit   map[string]int     // 每城市的估算单元上限（观测）
	CityReqTotals    map[string]int     // 每城市的总请求量（观测）
	CityCurrentCount map[string]int     // 每城市现有机器数（观测）
}

// NewGlobalBalanceCoordinator 创建全局均衡协调器
func NewGlobalBalanceCoordinator(param RequestInputParam) *GlobalBalanceCoordinator {
	coordinator := &GlobalBalanceCoordinator{
		RequestParam:      param,
		GlobalDistribute:  make(map[string]int),
		GlobalRackDistrib: make(map[string]int),
		AllAffinities:     param.GetAllAffinities(),
		AllResourcePools:  make(map[string][]model.TbRpDetail),
		CurrentUnitCounts: make(map[string]int),
		CityTolerance:     make(map[string]float64),
		CityMaxPerUnit:    make(map[string]int),
		CityReqTotals:     make(map[string]int),
		CityCurrentCount:  make(map[string]int),
	}

	// 计算总请求数量
	for _, detail := range param.Details {
		coordinator.TotalRequestCount += detail.Count
	}

	// 统计所有当前主机分布和确定分配级别
	coordinator.analyzeGlobalDistribution()

	return coordinator
}

// analyzeGlobalDistribution 分析全局分布情况
func (gc *GlobalBalanceCoordinator) analyzeGlobalDistribution() {
	// 统计所有现有主机分布
	allCurrentHosts := make([]CurrentResource, 0)
	toleranceSum := 0.0
	toleranceCount := 0
	// 按城市聚合观测数据
	cityTolSum := make(map[string]float64)
	cityTolCnt := make(map[string]int)

	for _, detail := range gc.RequestParam.Details {
		allCurrentHosts = append(allCurrentHosts, detail.CurrentHosts...)
		if detail.Tolerance >= 0 {
			toleranceSum += detail.Tolerance
			toleranceCount++
		}
		// 城市观测：将请求和容忍度按城市聚合
		city := detail.LocationSpec.City
		if city != "" {
			gc.CityReqTotals[city] += detail.Count
			if detail.Tolerance >= 0 {
				cityTolSum[city] += detail.Tolerance
				cityTolCnt[city]++
			}
			// 假设当前主机与该请求处于同城（用于观测统计）
			gc.CityCurrentCount[city] += len(detail.CurrentHosts)
		}
	}

	// 计算平均容忍度
	if toleranceCount > 0 {
		gc.GlobalTolerance = toleranceSum / float64(toleranceCount)
	}

	// 确定是否使用机架级分配
	gc.IsRackLevel = slices.Contains([]string{SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH, CROSS_RACK}, gc.AllAffinities[0])

	// 统计当前分布
	if gc.IsRackLevel {
		// 机架级统计
		for _, host := range allCurrentHosts {
			if host.RackId != "" {
				gc.CurrentUnitCounts[host.RackId]++
				gc.GlobalRackDistrib[host.RackId]++
			}
		}
	} else {
		// 园区级统计
		for _, host := range allCurrentHosts {
			if host.SubZone != "" {
				gc.CurrentUnitCounts[host.SubZone]++
				gc.GlobalDistribute[host.SubZone]++
			}
		}
	}

	// 计算城市观测的 MaxPerUnit（仅观测）
	for city, cnt := range cityTolCnt {
		if cnt == 0 {
			continue
		}
		avgTol := cityTolSum[city] / float64(cnt)
		gc.CityTolerance[city] = avgTol
		totalMachinesCity := gc.CityCurrentCount[city] + gc.CityReqTotals[city]
		if avgTol == 0 {
			gc.CityMaxPerUnit[city] = 1
		} else {
			gc.CityMaxPerUnit[city] = int(math.Ceil(float64(totalMachinesCity) * avgTol))
		}
	}

	logger.Info("全局分配分析: 总请求=%d, 现有主机=%d, 是否机架级=%v",
		gc.TotalRequestCount, len(allCurrentHosts), gc.IsRackLevel)
	// 输出城市观测信息
	for city := range gc.CityReqTotals {
		logger.Info("城市观测: city=%s req_total=%d current=%d tol=%.2f city_max=%d",
			city, gc.CityReqTotals[city], gc.CityCurrentCount[city], gc.CityTolerance[city], gc.CityMaxPerUnit[city])
	}
}

// PrepareAllContexts 准备所有请求的上下文和资源池
func (gc *GlobalBalanceCoordinator) PrepareAllContexts(details []ObjectDetail) ([]*SearchContext, error) {
	cityMapCache := cache.New(2*time.Minute, 30*time.Second)
	defer cityMapCache.Flush()

	for _, detail := range details {
		// 创建搜索上下文
		idcCites := []string{}
		if lo.IsNotEmpty(&detail.LocationSpec.City) {
			var err error
			idcCites, err = getLogicIdcCitys(detail)
			if err != nil {
				return nil, fmt.Errorf("get logic cities failed: %v", err)
			}
		}

		context := &SearchContext{
			IntentionBkBizId: gc.RequestParam.ForbizId,
			RsType:           gc.RequestParam.ResourceType,
			ObjectDetail:     &detail,
			IdcCitys:         idcCites,
			SpecialHostIds:   detail.Hosts.GetBkHostIds(),
		}

		if err := context.PickCheck(); err != nil {
			return nil, fmt.Errorf("pick check failed for %s: %v", detail.GroupMark, err)
		}

		// 获取可用资源
		resources, err := gc.getAvailableResources(context)
		if err != nil {
			return nil, fmt.Errorf("get resources failed for %s: %v", detail.GroupMark, err)
		}

		// 按园区组织资源
		gc.organizeResourcesBySubZone(resources)
		gc.RequestContexts = append(gc.RequestContexts, context)
	}

	logger.Info("准备完成，共%d个请求上下文，资源池覆盖%d个园区",
		len(gc.RequestContexts), len(gc.AllResourcePools))
	return gc.RequestContexts, nil
}

// getAvailableResources 获取可用资源
func (gc *GlobalBalanceCoordinator) getAvailableResources(context *SearchContext) ([]model.TbRpDetail, error) {
	var items []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName())
	context.pickBase(db)
	if err := db.Scan(&items).Error; err != nil {
		return nil, fmt.Errorf("query resources failed: %v", err)
	}

	// 过滤空挂载点的磁盘
	diskSpecs := meta.GetEmptyDiskSpec(context.StorageSpecs)
	if len(diskSpecs) > 0 && len(context.SpecialHostIds) == 0 {
		filteredItems, err := context.filterEmptyMountPointStorage(items, diskSpecs)
		if err != nil {
			return nil, fmt.Errorf("filter storage failed: %v", err)
		}
		items = filteredItems
	}

	return items, nil
}

// organizeResourcesBySubZone 按园区组织资源（按 BkHostID 去重）
func (gc *GlobalBalanceCoordinator) organizeResourcesBySubZone(resources []model.TbRpDetail) {
	seen := make(map[string]map[int]struct{})
	// 预热已存在的资源，避免多次调用时重复累积
	for subZone, exists := range gc.AllResourcePools {
		if _, ok := seen[subZone]; !ok {
			seen[subZone] = make(map[int]struct{})
		}
		for _, r := range exists {
			seen[subZone][r.BkHostID] = struct{}{}
		}
	}
	for _, resource := range resources {
		subZone := resource.SubZone
		if _, exists := gc.AllResourcePools[subZone]; !exists {
			gc.AllResourcePools[subZone] = make([]model.TbRpDetail, 0)
		}
		if _, ok := seen[subZone]; !ok {
			seen[subZone] = make(map[int]struct{})
		}
		if _, exists := seen[subZone][resource.BkHostID]; exists {
			continue
		}
		seen[subZone][resource.BkHostID] = struct{}{}
		gc.AllResourcePools[subZone] = append(gc.AllResourcePools[subZone], resource)
	}
}

// GlobalBalancedAllocation 全局均衡分配
func (gc *GlobalBalanceCoordinator) GlobalBalancedAllocation(contexts []*SearchContext) ([]*PickerObject, error) {
	var pickers []*PickerObject

	// 创建全局资源分配状态跟踪
	globalState := &GlobalAllocationState{
		UnitCounts:  make(map[string]int),
		RackCounts:  make(map[string]int),
		UsedHostIds: make(map[int]bool),
		MaxPerUnit:  gc.MaxPerUnit,
		IsRackLevel: gc.IsRackLevel,
		Tolerance:   gc.GlobalTolerance,
	}

	// 初始化已存在的分布
	for unit, count := range gc.CurrentUnitCounts {
		globalState.UnitCounts[unit] = count
		if gc.IsRackLevel {
			globalState.RackCounts[unit] = count
		}
	}

	// 输出全局分配开始信息
	gc.logGlobalAllocationStart(contexts)

	// 按优先级分配每个请求
	for i, context := range contexts {
		logger.Info("🎯 === 开始分配组 %s (%d/%d) ===", context.GroupMark, i+1, len(contexts))

		picker, err := gc.allocateForContext(context, globalState)
		if err != nil {
			logger.Error("❌ 组 %s 分配失败: %v", context.GroupMark, err)
			return nil, fmt.Errorf("allocate failed for %s: %v", context.GroupMark, err)
		}

		pickers = append(pickers, picker)
		logger.Info("✅ 完成组 %s 的分配: %d台机器 (%.1f%%)",
			context.GroupMark, len(picker.SatisfiedHostIds),
			float64(len(picker.SatisfiedHostIds))/float64(context.ObjectDetail.Count)*100)
		logger.Info("=====================================")
	}

	// 输出全局分配统计
	gc.logGlobalAllocationResult(globalState)
	return pickers, nil
}

// GlobalAllocationState 全局分配状态
type GlobalAllocationState struct {
	UnitCounts  map[string]int // 单元(园区/机架)计数
	RackCounts  map[string]int // 机架计数(仅机架级使用)
	UsedHostIds map[int]bool   // 已使用的主机ID
	MaxPerUnit  int            // 每单元最大数量
	IsRackLevel bool           // 是否机架级
	Tolerance   float64        // 容忍度
}

// allocateForContext 为特定上下文分配资源
func (gc *GlobalBalanceCoordinator) allocateForContext(context *SearchContext, globalState *GlobalAllocationState) (*PickerObject, error) {
	picker := NewPicker(context.Count, context.GroupMark)

	// 选择本组的容忍度，优先使用请求自身的 Tolerance，其次使用全局容忍度
	selectedTolerance := gc.GlobalTolerance
	if context.Tolerance >= 0 {
		selectedTolerance = context.Tolerance
	}

	// 根据分配级别初始化容忍度配置
	if gc.IsRackLevel {
		picker.InitRackToleranceConfig(selectedTolerance, context.CurrentHosts, context.Count)
	} else {
		picker.InitToleranceConfig(selectedTolerance, context.CurrentHosts, context.Count)
	}

	// 获取优先级资源
	priorityElements, prioritySumMap, err := context.AnalysisResourcePriority(
		gc.getResourcesForContext(), false)
	if err != nil {
		return nil, fmt.Errorf("analyze priority failed: %v", err)
	}

	picker.PriorityElements = priorityElements
	picker.SubZonePrioritySumMap = prioritySumMap

	// 使用全局均衡分配策略
	err = gc.globalBalancedPick(picker, globalState)
	if err != nil {
		return nil, fmt.Errorf("global balanced pick failed: %v", err)
	}

	if !picker.PickerDone() {
		return nil, fmt.Errorf("insufficient resources for %s, allocated: %d, required: %d",
			context.GroupMark, len(picker.SatisfiedHostIds), context.Count)
	}

	return picker, nil
}

// getResourcesForContext 获取特定上下文的资源
func (gc *GlobalBalanceCoordinator) getResourcesForContext() []model.TbRpDetail {
	var resources []model.TbRpDetail

	// 收集相关园区的资源
	for _, subZoneResources := range gc.AllResourcePools {
		resources = append(resources, subZoneResources...)
	}

	return resources
}

// globalBalancedPick 全局均衡选择
func (gc *GlobalBalanceCoordinator) globalBalancedPick(picker *PickerObject,
	globalState *GlobalAllocationState) error {
	for !picker.PickerDone() {
		allocated := false

		// 获取按可用容量排序的单元列表（容量大的优先）- 考虑本组容忍度余量
		sortedUnits := gc.getSortedUnitsByAvailableCapacityWithPicker(globalState, picker)
		if len(sortedUnits) == 0 {
			break
		}

		// 轮询各单元尝试分配
		for _, unit := range sortedUnits {
			if gc.allocateOneFromUnit(picker, unit, globalState) {
				allocated = true
				break
			}
		}

		if !allocated {
			break
		}
	}

	return nil
}

// getSortedUnitsByAvailableCapacity 兼容旧签名（不考虑特定分组余量）
func (gc *GlobalBalanceCoordinator) getSortedUnitsByAvailableCapacity(
	globalState *GlobalAllocationState) []string {
	return gc.getSortedUnitsByAvailableCapacityWithPicker(globalState, nil)
}

// getSortedUnitsByAvailableCapacityWithPicker 按可用容量排序单元（容量大的优先，兼顾均衡与本组余量）
func (gc *GlobalBalanceCoordinator) getSortedUnitsByAvailableCapacityWithPicker(
	globalState *GlobalAllocationState, picker *PickerObject) []string {
	type unitCapacity struct {
		unit              string
		allocatedCount    int     // 本【园区/机架】 已分配数量（全局）
		availableCount    int     // 本【园区/机架】 可用资源数量
		remainingCapacity int     // 本【园区/机架】 全局需要的容量 = 全局容忍上限 - 已分配
		pickerHeadroom    int     // 本【园区/机架】 本组还需要的容量 = 本组容忍上限 - (本组已存在+已分配)
		score             float64 // 综合评分
	}

	minInt := func(a, b int) int {
		if a < b {
			return a
		}
		return b
	}

	var units []unitCapacity
	processedUnits := make(map[string]bool)

	// 收集所有可用单元的容量信息
	for zoneName, resources := range gc.AllResourcePools {
		if gc.IsRackLevel {
			// 机架级分配：按机架统计
			rackResources := make(map[string]int)
			for _, resource := range resources {
				if resource.RackID != "" {
					rackResources[resource.RackID]++
				}
			}

			for rackId, availableCount := range rackResources {
				if processedUnits[rackId] {
					continue
				}
				processedUnits[rackId] = true

				allocatedCount := globalState.RackCounts[rackId]
				remainingCapacity := gc.MaxPerUnit - allocatedCount // 仅用于评分，不做硬过滤

				// 计算本组在该机架的余量
				pickerRemaining := 0
				if picker != nil {
					pickerRemaining = picker.MaxPerRack - picker.GetRackCurrentTotal(rackId)
				}

				if availableCount > 0 && (picker == nil || pickerRemaining > 0) {
					// 计算综合评分：可用资源多、全局剩余容量大、本组余量足 的优先
					effRemaining := remainingCapacity
					if picker != nil {
						effRemaining = minInt(remainingCapacity, pickerRemaining)
					}
					if effRemaining < 0 {
						effRemaining = 0
					}
					score := gc.calculateUnitScore(availableCount, allocatedCount, effRemaining)
					units = append(units, unitCapacity{
						unit:              rackId,
						allocatedCount:    allocatedCount,
						availableCount:    availableCount,
						remainingCapacity: remainingCapacity,
						pickerHeadroom:    pickerRemaining,
						score:             score,
					})
				}
			}
			continue
		}

		// 园区级分配
		if processedUnits[zoneName] {
			continue
		}
		processedUnits[zoneName] = true

		allocatedCount := globalState.UnitCounts[zoneName]
		remainingCapacity := gc.MaxPerUnit - allocatedCount // 仅用于评分，不做硬过滤
		availableCount := len(resources)

		// 计算本组在该园区的余量
		pickerRemaining := 0
		if picker != nil {
			pickerRemaining = picker.MaxPerSubZone - picker.GetSubZoneCurrentTotal(zoneName)
		}

		if availableCount > 0 && (picker == nil || pickerRemaining > 0) {
			effRemaining := remainingCapacity
			if picker != nil {
				effRemaining = minInt(remainingCapacity, pickerRemaining)
			}
			if effRemaining < 0 {
				effRemaining = 0
			}
			score := gc.calculateUnitScore(availableCount, allocatedCount, effRemaining)
			units = append(units, unitCapacity{
				unit:              zoneName,
				allocatedCount:    allocatedCount,
				availableCount:    availableCount,
				remainingCapacity: remainingCapacity,
				pickerHeadroom:    pickerRemaining,
				score:             score,
			})
		}
	}

	// 按综合评分降序排序（评分高的优先分配）
	sort.Slice(units, func(i, j int) bool {
		return units[i].score > units[j].score
	})

	result := make([]string, len(units))
	for i, u := range units {
		result[i] = u.unit
	}

	logger.Debug("单元分配优先级排序完成，共%d个可用单元", len(result))
	return result
}

// calculateUnitScore 计算单元的综合评分
func (gc *GlobalBalanceCoordinator) calculateUnitScore(availableCount, allocatedCount, remainingCapacity int) float64 {
	if availableCount == 0 || remainingCapacity <= 0 {
		return 0
	}

	// 评分因子
	var (
		availableWeight = 0.5 // 可用资源权重
		capacityWeight  = 0.3 // 剩余容量权重
		balanceWeight   = 0.2 // 均衡因子权重
	)

	// 可用资源评分 (归一化到0-1)
	availableScore := math.Log(float64(availableCount + 1)) // 使用对数避免极值影响

	// 剩余容量评分
	capacityScore := float64(remainingCapacity) / float64(gc.MaxPerUnit)

	// 均衡因子：已分配数量越少，均衡分越高
	maxAllocated := float64(gc.MaxPerUnit)
	balanceScore := (maxAllocated - float64(allocatedCount)) / maxAllocated

	// 综合评分
	totalScore := availableWeight*availableScore +
		capacityWeight*capacityScore +
		balanceWeight*balanceScore

	return totalScore
}

// allocateOneFromUnit 从指定单元分配一台机器
func (gc *GlobalBalanceCoordinator) allocateOneFromUnit(picker *PickerObject, unit string, globalState *GlobalAllocationState) bool {
	// 根据分配级别选择分配逻辑
	if gc.IsRackLevel {
		return gc.allocateOneFromRack(picker, unit, globalState)
	}
	return gc.allocateOneFromSubZone(picker, unit, globalState)
}

// allocateOneFromRack 从指定机架分配一台机器
func (gc *GlobalBalanceCoordinator) allocateOneFromRack(picker *PickerObject, rackId string, globalState *GlobalAllocationState) bool {
	// 分配前检查该分组在该机架上的容忍度是否允许
	if picker.Tolerance >= 0 && picker.MaxPerRack > 0 {
		if !picker.CanAllocateToRack(rackId) {
			return false
		}
	}
	// 找到包含该机架的园区
	var targetSubZone string
	for subZone, resources := range gc.AllResourcePools {
		for _, resource := range resources {
			if resource.RackID == rackId {
				targetSubZone = subZone
				break
			}
		}
		if targetSubZone != "" {
			break
		}
	}

	if targetSubZone == "" {
		return false
	}

	// 从该园区的资源中选择指定机架的机器
	pq, ok := picker.PriorityElements[targetSubZone]
	if !ok || pq.Len() == 0 {
		return false
	}

	var tempItems []*Item
	defer func() {
		for _, item := range tempItems {
			if err := pq.Push(item); err != nil {
				logger.Error("failed to push item back: %v", err)
			}
		}
	}()

	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			continue
		}

		// 检查是否是目标机架且未被使用
		if v.RackId != rackId || globalState.UsedHostIds[v.BkHostId] {
			tempItems = append(tempItems, item)
			continue
		}

		// 分配成功
		picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostId)
		picker.PickDistribute[targetSubZone]++
		picker.RackDistribute[rackId]++
		globalState.UsedHostIds[v.BkHostId] = true
		globalState.RackCounts[rackId]++
		globalState.UnitCounts[targetSubZone]++

		logger.Debug("从机架 %s 分配主机 %d", rackId, v.BkHostId)
		return true
	}

	return false
}

// allocateOneFromSubZone 从指定园区分配一台机器
func (gc *GlobalBalanceCoordinator) allocateOneFromSubZone(picker *PickerObject, subZone string, globalState *GlobalAllocationState) bool {
	// 分配前检查该分组在该园区的容忍度是否允许
	if picker.Tolerance >= 0 && picker.MaxPerSubZone > 0 {
		if !picker.CanAllocateToSubZone(subZone) {
			return false
		}
	}
	pq, ok := picker.PriorityElements[subZone]
	if !ok || pq.Len() == 0 {
		return false
	}

	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			continue
		}

		if globalState.UsedHostIds[v.BkHostId] {
			continue
		}

		// 分配成功
		picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostId)
		picker.PickDistribute[subZone]++
		globalState.UsedHostIds[v.BkHostId] = true
		globalState.UnitCounts[subZone]++

		logger.Debug("从园区 %s 分配主机 %d", subZone, v.BkHostId)
		return true
	}

	return false
}

// logGlobalAllocationStart 输出全局分配开始信息
func (gc *GlobalBalanceCoordinator) logGlobalAllocationStart(contexts []*SearchContext) {
	logger.Info("🌍 === 开始全局均衡分配 ===")
	logger.Info("📊 分配概览: 总请求组数=%d, 总请求机器数=%d", len(contexts), gc.TotalRequestCount)
	logger.Info("🎯 分配级别: %s", map[bool]string{true: "机架级", false: "园区级"}[gc.IsRackLevel])
	logger.Info("⚖️  全局容忍度: %.2f", gc.GlobalTolerance)
	logger.Info("📏 单元最大机器数: %d", gc.MaxPerUnit)

	// 显示各组的请求详情
	logger.Info("📋 请求组详情:")
	for i, context := range contexts {
		logger.Info("  %d. 组 %s: 申请%d台机器", i+1, context.GroupMark, context.ObjectDetail.Count)
	}

	// 显示初始资源分布
	logger.Info("📍 初始资源分布:")
	if gc.IsRackLevel {
		for rackId, count := range gc.CurrentUnitCounts {
			logger.Info("  🏗️  机架 %s: 已存在机器=%d", rackId, count)
		}
	} else {
		for subZone, count := range gc.CurrentUnitCounts {
			logger.Info("  🏢 园区 %s: 已存在机器=%d", subZone, count)
		}
	}
	logger.Info("===============================")
}

// logGlobalAllocationResult 输出全局分配结果
func (gc *GlobalBalanceCoordinator) logGlobalAllocationResult(globalState *GlobalAllocationState) {
	logger.Info("🏁 === 全局均衡分配结果 ===")
	logger.Info("📊 总请求数量: %d", gc.TotalRequestCount)
	logger.Info("🎯 分配级别: %s", map[bool]string{true: "机架级", false: "园区级"}[gc.IsRackLevel])
	logger.Info("⚖️  全局容忍度: %.2f", gc.GlobalTolerance)
	logger.Info("📏 单元最大机器数: %d", gc.MaxPerUnit)

	if gc.IsRackLevel {
		logger.Info("🏗️  机架机器分布:")
		for rackId, count := range globalState.RackCounts {
			existing := gc.CurrentUnitCounts[rackId]
			newAllocated := count - existing
			logger.Info("  🏗️  机架 %s: 已存在=%d, 新分配=%d, 总计=%d",
				rackId, existing, newAllocated, count)
		}
	} else {
		logger.Info("🏢 园区机器分布:")
		for subZone, count := range globalState.UnitCounts {
			existing := gc.CurrentUnitCounts[subZone]
			newAllocated := count - existing
			logger.Info("  🏢 园区 %s: 已存在=%d, 新分配=%d, 总计=%d",
				subZone, existing, newAllocated, count)
		}
	}

	logger.Info("===============================")
}
