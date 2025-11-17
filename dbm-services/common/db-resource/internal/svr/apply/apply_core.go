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

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	mapset "github.com/deckarep/golang-set/v2"
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
	Tolerance             float64         // 园区级容忍度参数
	CurrentHostsBySubZone map[subZone]int // 当前集群已存在资源按园区分组的数量
	TotalCount            int             // 总数量（申请数量 + 当前已存在数量）
	MaxPerSubZone         int             // 每个园区最大容忍机器数量

	// 机架级别容忍度相关字段 - 用于SAME_SUBZONE跨机架亲和性和双容忍度场景
	RackTolerance      float64        // 机架级容忍度参数（用于双容忍度场景）
	CurrentHostsByRack map[string]int // 当前集群已存在资源按机架分组的数量
	MaxPerRack         int            // 每个机架最大容忍机器数量
	RackDistribute     map[string]int // 当前分配中各机架的机器数量

	// MAJORITY_ELECTION_DISTRI 按园区跟踪机架 - 用于确保同一园区内的机器跨机架
	RackIdsBySubZone map[subZone][]string // 每个园区已使用的机架ID列表
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
		RackIdsBySubZone:      make(map[subZone][]string),
		Tolerance:             -1, // 默认值-1表示未设置园区级容忍度
		RackTolerance:         -1, // 默认值-1表示未设置机架级容忍度
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

// CrossRackCheckInSubZone 检查指定机架是否在指定园区内已使用
// 用于 MAJORITY_ELECTION_DISTRI 策略，确保同一园区内的机器跨机架
func (c *PickerObject) CrossRackCheckInSubZone(subzone subZone, rackId string) bool {
	if cmutil.IsEmpty(rackId) {
		return false
	}
	rackIds := c.RackIdsBySubZone[subzone]
	logger.Info("CrossRackCheckInSubZone, subzone: %s, rackId: %s, rackIds: %v", subzone, rackId, rackIds)
	return !slices.Contains(rackIds, rackId)
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

	// 统计当前主机在各个园区的分布，并记录每个园区已使用的机架ID
	for _, host := range currentHosts {
		subzone := strings.TrimSpace(host.SubZone)
		c.CurrentHostsBySubZone[subzone]++
		// 记录当前主机所在园区的机架ID（用于 MAJORITY_ELECTION_DISTRI 场景的跨机架检查）
		if cmutil.IsNotEmpty(host.RackId) {
			logger.Info("InitToleranceConfig, subzone: %s, rackId: %s", host.SubZone, host.RackId)
			c.RackIdsBySubZone[subzone] = append(c.RackIdsBySubZone[subzone], host.RackId)
		}
	}
	logger.Info("RackIdsBySubZone: %v", c.RackIdsBySubZone)

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
func (c *PickerObject) InitRackForCrossRack(currentHosts []CurrentResource) {
	c.CurrentHostsByRack = make(map[string]int)
	c.RackDistribute = make(map[string]int)
	for _, host := range currentHosts {
		if host.RackId != "" {
			rackKey := buildRackKey(RANDOM, host.RackId)
			c.CurrentHostsByRack[rackKey]++
			c.RackDistribute[rackKey]++
		}
	}
}

// InitRackToleranceConfig 初始化机架级别的容忍度相关配置
func (c *PickerObject) InitRackToleranceConfig(tolerance float64, currentHosts []CurrentResource, requestCount int) {
	c.Tolerance = tolerance
	c.RackTolerance = tolerance // 机架级容忍度与园区级容忍度相同（用于SAME_SUBZONE等场景）
	c.CurrentHostsByRack = make(map[string]int)
	c.RackDistribute = make(map[string]int)

	// 统计当前主机在各个机架的分布
	for _, host := range currentHosts {
		if host.RackId != "" {
			rackKey := buildRackKey(host.SubZone, host.RackId)
			c.CurrentHostsByRack[rackKey]++
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

func buildRackKey(subzone, rackId string) string {
	return fmt.Sprintf("%s-%s", subzone, rackId)
}

// InitDualToleranceConfig 初始化双容忍度配置（同时支持园区级和机架级容忍度）
// 用于 CROSS_SUBZONE_STRONG 和 CROSS_SUBZONE_WEAK 策略
func (c *PickerObject) InitDualToleranceConfig(
	subzoneTolerance float64,
	rackTolerance float64,
	currentHosts []CurrentResource,
	requestCount int,
) {
	c.Tolerance = subzoneTolerance  // 园区级容忍度
	c.RackTolerance = rackTolerance // 机架级容忍度
	c.CurrentHostsBySubZone = make(map[subZone]int)
	c.CurrentHostsByRack = make(map[string]int)
	c.RackDistribute = make(map[string]int)
	if c.RackIdsBySubZone == nil {
		c.RackIdsBySubZone = make(map[subZone][]string)
	}

	// 统计当前主机在各个园区和机架的分布
	for _, host := range currentHosts {
		subzone := strings.TrimSpace(host.SubZone)
		c.CurrentHostsBySubZone[subzone]++
		// 记录当前主机所在园区的机架ID
		if cmutil.IsNotEmpty(host.RackId) {
			rackKey := buildRackKey(subzone, host.RackId)
			c.CurrentHostsByRack[rackKey]++
			c.RackIdsBySubZone[rackKey] = append(c.RackIdsBySubZone[rackKey], host.RackId)
		}
	}

	// 计算总数量
	currentTotalCount := len(currentHosts)
	c.TotalCount = currentTotalCount + requestCount

	// 计算每个园区最大容忍机器数量
	if subzoneTolerance == 0 {
		c.MaxPerSubZone = 1
	} else {
		c.MaxPerSubZone = int(math.Ceil(float64(c.TotalCount) * subzoneTolerance))
	}

	// 计算每个机架最大容忍机器数量（基于每个园区的最大机器数）
	if rackTolerance == 0 {
		c.MaxPerRack = 1
	} else {
		c.MaxPerRack = int(math.Ceil(float64(c.MaxPerSubZone) * rackTolerance))
	}

	logger.Info("双容忍度配置: subzoneTolerance=%.2f, rackTolerance=%.2f, totalCount=%d, maxPerSubZone=%d, maxPerRack=%d",
		subzoneTolerance, rackTolerance, c.TotalCount, c.MaxPerSubZone, c.MaxPerRack)
	logger.Info("当前园区分布: %v", c.CurrentHostsBySubZone)
	logger.Info("当前机架分布: %v", c.CurrentHostsByRack)
	logger.Info("园区机架映射: %v", c.RackIdsBySubZone)
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
func (c *PickerObject) CanAllocateToRack(subzone, rackId string) bool {
	// 如果没有设置机架级容忍度限制，直接允许分配
	if c.MaxPerRack == 0 {
		return true
	}

	// 确定使用的机架级容忍度：优先使用RackTolerance，否则使用Tolerance（向后兼容）
	rackTolerance := c.RackTolerance
	if rackTolerance == -1 {
		rackTolerance = c.Tolerance
	}
	rackKey := buildRackKey(subzone, rackId)
	// tolerance为0时，必须跨机架，检查该机架是否已经有机器
	if rackTolerance == 0 {
		currentCount := c.CurrentHostsByRack[rackKey]
		allocatedCount := c.RackDistribute[rackKey]
		return currentCount+allocatedCount == 0
	}

	// 检查该机架当前总数是否超过容忍限制
	currentCount := c.CurrentHostsByRack[rackKey]
	allocatedCount := c.RackDistribute[rackKey]
	totalInRack := currentCount + allocatedCount

	return totalInRack < c.MaxPerRack
}

// GetRackCurrentTotal 获取指定机架当前总机器数（包括已存在的和已分配的）
func (c *PickerObject) GetRackCurrentTotal(subzone, rackId string) int {
	rackKey := buildRackKey(subzone, rackId)
	currentCount := c.CurrentHostsByRack[rackKey]
	allocatedCount := c.RackDistribute[rackKey]
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
			if !c.CanAllocateToRack(subZone, rackId) {
				continue
			}
		}

		currentTotal := c.GetRackCurrentTotal(subZone, rackId)
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
