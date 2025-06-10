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
	"strconv"
	"strings"
	"time"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// PickerRandom 随机匹配
func (c *PickerObject) PickerRandom() {
	logger.Info("random match resource ...")
	pq, ok := c.PriorityElements[RANDOM]
	if !ok {
		logger.Error("not exist %s", RANDOM)
		return
	}
	logger.Info("random priority have %d machine", pq.Len())
	for pq.Len() > 0 {
		c.pickerOneByPriority(RANDOM, false)
		logger.Info("%d,%d", c.Count, len(c.SatisfiedHostIds))
		// 匹配资源完成
		if c.PickerDone() {
			return
		}
	}
}

// PickerSameSubZone 同园区资源匹配
func (c *PickerObject) PickerSameSubZone(cross_switch bool) {
	// 如果设置了容忍度，使用机架均衡分配策略
	if c.Tolerance >= 0 && c.MaxPerRack > 0 {
		c.PickerSameSubZoneBalanced(cross_switch)
		return
	}

	// 原有的同园区分配逻辑
	sortSubZones := c.sortSubZoneNum(false)
	if len(sortSubZones) == 0 {
		return
	}
	for _, subzone := range sortSubZones {
		pq := c.PriorityElements[subzone]
		if pq.Len() < c.Count || pq.Len() == 0 {
			c.ProcessLogs = append(c.ProcessLogs, fmt.Sprintf("%s 符合条件的资源有%d,实际需要申请%d,不满足！！！",
				subzone, pq.Len(), c.Count))
			continue
		}
		logger.Info("debug %v", subzone)
		c.SatisfiedHostIds = []int{}
		c.ExistRackIds = []string{}
		c.ExistLinkNetdeviceIds = []string{}
		for pq.Len() > 0 {
			c.pickerOneByPriority(subzone, cross_switch)
			logger.Info(fmt.Sprintf("%s,%d,%d", subzone, c.Count, len(c.SatisfiedHostIds)))
			if c.PickerDone() {
				return
			}
		}
	}
}

// PickerSameSubZoneBalanced 同园区机架均衡资源匹配
func (c *PickerObject) PickerSameSubZoneBalanced(cross_switch bool) {
	sortSubZones := c.sortSubZoneNum(false)
	if len(sortSubZones) == 0 {
		return
	}

	logger.Info("开始同园区机架均衡分配")

	for _, subzone := range sortSubZones {
		pq := c.PriorityElements[subzone]
		if pq.Len() < c.Count || pq.Len() == 0 {
			c.ProcessLogs = append(c.ProcessLogs, fmt.Sprintf("%s 符合条件的资源有%d,实际需要申请%d,不满足！！！",
				subzone, pq.Len(), c.Count))
			continue
		}

		logger.Info("在园区 %s 中进行机架均衡分配", subzone)
		c.SatisfiedHostIds = []int{}
		c.ExistRackIds = []string{}
		c.ExistLinkNetdeviceIds = []string{}

		// 使用机架均衡分配策略
		if c.pickerSameSubZoneRackBalanced(subzone, cross_switch) {
			return
		}
	}
}

// pickerSameSubZoneRackBalanced 在同园区内进行机架均衡分配
func (c *PickerObject) pickerSameSubZoneRackBalanced(subzone string, cross_switch bool) bool {
	// 记录上次重新排序的分配数量
	lastRebalanceAt := 0

	for !c.PickerDone() {
		// 每分配几台机器后，检查是否需要重新排序以保持机架均衡
		currentAllocated := len(c.SatisfiedHostIds)

		var rackKeys []string
		if currentAllocated > lastRebalanceAt && (currentAllocated-lastRebalanceAt) >= 3 {
			// 重新获取机架均衡排序
			rackKeys = c.SortRackByBalance(subzone)
			lastRebalanceAt = currentAllocated
		} else {
			// 第一次或者间隔不够时，使用机架均衡排序
			rackKeys = c.SortRackByBalance(subzone)
		}

		if len(rackKeys) == 0 {
			logger.Info("园区 %s 没有可用的机架", subzone)
			break
		}

		allocated := false

		// 轮询各机架进行分配
		for _, rackId := range rackKeys {
			// 检查机架容忍度限制
			if !c.CanAllocateToRack(rackId) {
				logger.Debug("机架 %s 已达到容忍度限制，跳过", rackId)
				continue
			}

			// 尝试从该机架分配一台机器
			if c.pickerOneFromRack(subzone, rackId, cross_switch) {
				allocated = true
				logger.Info("成功从机架 %s 分配一台机器，当前总分配: %d/%d，机架当前机器数: %d",
					rackId, len(c.SatisfiedHostIds), c.Count, c.GetRackCurrentTotal(rackId))

				if c.PickerDone() {
					c.logFinalRackDistribution(subzone)
					return true
				}
				break // 分配成功后重新开始轮询
			}
		}

		// 如果本轮没有成功分配任何机器，退出循环
		if !allocated {
			logger.Info("本轮未能分配任何机器，退出机架均衡分配")
			break
		}
	}

	return c.PickerDone()
}

// pickerOneFromRack 从指定机架中分配一台机器
func (c *PickerObject) pickerOneFromRack(subzone, rackId string, cross_switch bool) bool {
	pq, ok := c.PriorityElements[subzone]
	if !ok || pq.Len() == 0 {
		return false
	}

	// 临时存储不匹配的机器，稍后放回队列
	var tempItems []*Item
	defer func() {
		// 将未被选中的机器放回队列
		for _, item := range tempItems {
			if err := pq.Push(item); err != nil {
				logger.Error("failed to push item back to queue: %v", err)
			}
		}
	}()

	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			logger.Warn("Type Assertion failed,hostId:%s", item.Key)
			continue
		}

		// 检查是否是目标机架的机器
		if v.RackId != rackId {
			tempItems = append(tempItems, item)
			continue
		}

		// 跨交换机检查
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				tempItems = append(tempItems, item)
				continue
			}
		}

		// 检查是否已经被选中
		if slices.Contains(c.SatisfiedHostIds, v.BkHostId) {
			tempItems = append(tempItems, item)
			continue
		}

		// 分配成功
		c.ExistRackIds = append(c.ExistRackIds, v.RackId)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistribute[subzone]++
		c.RackDistribute[v.RackId]++
		return true
	}

	return false
}

// logFinalRackDistribution 输出最终的机架分配统计信息
func (c *PickerObject) logFinalRackDistribution(subzone string) {
	if len(c.RackDistribute) == 0 {
		return
	}

	logger.Info("=== 最终机架分配统计 (园区%s) ===", subzone)
	totalAllocated := len(c.SatisfiedHostIds)

	logger.Info("总申请数量: %d, 总分配数量: %d", c.Count, totalAllocated)

	if c.Tolerance >= 0 {
		logger.Info("容忍度: %.2f, 每机架最大允许: %d", c.Tolerance, c.MaxPerRack)
	}

	// 输出各机架分配详情
	for rackId, allocated := range c.RackDistribute {
		existing := c.CurrentHostsByRack[rackId]
		total := existing + allocated
		logger.Info("机架 %s: 已存在=%d, 新分配=%d, 总计=%d", rackId, existing, allocated, total)
	}

	// 输出仅有已存在机器的机架
	for rackId, existing := range c.CurrentHostsByRack {
		if _, allocated := c.RackDistribute[rackId]; !allocated && existing > 0 {
			logger.Info("机架 %s: 已存在=%d, 新分配=0, 总计=%d", rackId, existing, existing)
		}
	}

	logger.Info("============================")
}

// PickerCrossSubzone 跨园区匹配
func (c *PickerObject) PickerCrossSubzone(cross_subzone, cross_switch bool) {
	// 定义排序策略：优先使用均衡排序，如果均衡排序无法找到足够资源，再使用原有策略
	sortFuncs := []func(cross_subzone bool) []string{
		c.SortSubZoneByBalance,  // 新增的均衡排序策略
		c.sortSubZoneByPriority, // 原有的优先级排序
		c.sortSubZoneNum,        // 原有的数量排序
	}

	for funcIndex, sfc := range sortFuncs {
		campKeys := sfc(cross_subzone)
		if len(campKeys) == 0 {
			logger.Info("排序函数 %d 未返回可用园区", funcIndex)
			continue
		}

		logger.Info("使用排序策略 %d，获得园区顺序: %v", funcIndex, campKeys)

		// 如果是均衡排序策略，使用轮询方式分配
		if funcIndex == 0 && c.Tolerance >= 0 && c.MaxPerSubZone > 0 {
			c.pickerCrossSubzoneBalanced(campKeys, cross_subzone, cross_switch)
		} else {
			// 使用原有的channel方式分配
			c.pickerCrossSubzoneOriginal(campKeys, cross_subzone, cross_switch)
		}

		// 如果已经完成分配，直接返回
		if c.PickerDone() {
			logger.Info("使用排序策略 %d 成功完成资源分配", funcIndex)
			return
		}
	}
}

// pickerCrossSubzoneBalanced 使用均衡策略分配资源
func (c *PickerObject) pickerCrossSubzoneBalanced(campKeys []string, cross_subzone, cross_switch bool) {
	if len(campKeys) == 0 {
		return
	}

	logger.Info("开始均衡分配，园区顺序: %v", campKeys)

	// 记录上次重新排序的分配数量
	lastRebalanceAt := 0

	// 在有可用园区的情况下持续分配
	for len(campKeys) > 0 && !c.PickerDone() {
		allocated := false

		// 每分配几台机器后，检查是否需要重新排序以保持均衡
		currentAllocated := len(c.SatisfiedHostIds)
		if currentAllocated > lastRebalanceAt && (currentAllocated-lastRebalanceAt) >= 3 {
			if c.ShouldRebalance() {
				logger.Info("检测到不均衡，重新排序园区")
				// 重新获取均衡排序的园区顺序
				newKeys := c.SortSubZoneByBalance(cross_subzone)
				if len(newKeys) > 0 {
					campKeys = newKeys
					lastRebalanceAt = currentAllocated
					logger.Info("重新排序后的园区顺序: %v", campKeys)
				}
			}
		}

		// 遍历所有园区，尝试分配一台机器
		for i := 0; i < len(campKeys); i++ {
			subzone := campKeys[i]

			pq, ok := c.PriorityElements[subzone]
			if !ok || pq.Len() == 0 {
				// 移除没有资源的园区
				campKeys = append(campKeys[:i], campKeys[i+1:]...)
				i-- // 调整索引
				continue
			}

			// 检查是否可以分配到该园区
			if c.Tolerance >= 0 && c.MaxPerSubZone > 0 {
				if !c.CanAllocateToSubZone(subzone) {
					logger.Debug("园区 %s 已达到容忍度限制，从候选移除", subzone)
					// 从候选列表中移除，避免反复遍历导致潜在死循环
					delete(c.PriorityElements, subzone)
					campKeys = append(campKeys[:i], campKeys[i+1:]...)
					i-- // 调整索引
					continue
				}
			}

			logger.Debug("尝试从园区 %s 分配资源，剩余: %d，当前机器数: %d",
				subzone, pq.Len(), c.GetSubZoneCurrentTotal(subzone))

			if c.pickerOneByPriority(subzone, cross_switch) {
				allocated = true
				logger.Info("成功从园区 %s 分配一台机器，当前总分配: %d/%d，园区当前机器数: %d",
					subzone, len(c.SatisfiedHostIds), c.Count, c.GetSubZoneCurrentTotal(subzone))

				if cross_subzone {
					// 跨园区模式：
					// - 容忍度为0时，严格跨园区，该园区只能取一台后移除
					// - 容忍度>0时，仅当该园区已无法继续分配（达到本组上限或无可用资源）才移除
					if c.Tolerance == 0 {
						delete(c.PriorityElements, subzone)
						campKeys = append(campKeys[:i], campKeys[i+1:]...)
						i-- // 调整索引
					} else {
						// 若该园区已达本组上限或队列无资源，则移除
						if !c.CanAllocateToSubZone(subzone) || pq.Len() == 0 {
							delete(c.PriorityElements, subzone)
							campKeys = append(campKeys[:i], campKeys[i+1:]...)
							i-- // 调整索引
						}
					}
				}

				if c.PickerDone() {
					// 输出最终分配统计
					c.logFinalDistribution()
					return
				}
				break // 分配成功后重新开始轮询
			}
		}

		// 如果本轮没有成功分配任何机器，退出循环
		if !allocated {
			logger.Info("本轮未能分配任何机器，退出均衡分配")
			break
		}
	}
}

// logFinalDistribution 输出最终的分配统计信息
func (c *PickerObject) logFinalDistribution() {
	if len(c.PickDistribute) == 0 {
		return
	}

	logger.Info("=== 最终分配统计 ===")
	totalAllocated := len(c.SatisfiedHostIds)
	balanceScore := c.CalculateBalanceScore()

	logger.Info("总申请数量: %d, 总分配数量: %d, 均衡得分: %.3f", c.Count, totalAllocated, balanceScore)

	if c.Tolerance >= 0 {
		logger.Info("容忍度: %.2f, 每园区最大允许: %d", c.Tolerance, c.MaxPerSubZone)
	}

	// 输出各园区分配详情
	for subZone, allocated := range c.PickDistribute {
		existing := c.CurrentHostsBySubZone[subZone]
		total := existing + allocated
		logger.Info("园区 %s: 已存在=%d, 新分配=%d, 总计=%d", subZone, existing, allocated, total)
	}

	// 输出仅有已存在机器的园区
	for subZone, existing := range c.CurrentHostsBySubZone {
		if _, allocated := c.PickDistribute[subZone]; !allocated && existing > 0 {
			logger.Info("园区 %s: 已存在=%d, 新分配=0, 总计=%d", subZone, existing, existing)
		}
	}

	logger.Info("==================")
}

// pickerCrossSubzoneOriginal 使用原有策略分配资源
func (c *PickerObject) pickerCrossSubzoneOriginal(campKeys []string, cross_subzone, cross_switch bool) {
	subzoneChan := make(chan subZone, len(campKeys))
	for _, v := range campKeys {
		subzoneChan <- v
	}

	for subzone := range subzoneChan {
		if len(c.PriorityElements) == 0 {
			logger.Info("go out")
			close(subzoneChan)
			return
		}
		pq, ok := c.PriorityElements[subzone]
		if !ok {
			logger.Warn("%s is queue is nil", subzone)
			delete(c.PriorityElements, subzone)
			continue
		}
		if pq.Len() == 0 {
			delete(c.PriorityElements, subzone)
		}
		if len(c.PriorityElements) == 0 {
			logger.Info("go out here")
			close(subzoneChan)
			return
		}
		logger.Info(fmt.Sprintf("surplus %s,%d", subzone, pq.Len()))
		logger.Info(fmt.Sprintf("%s,%d,%d", subzone, c.Count, len(c.SatisfiedHostIds)))
		if c.pickerOneByPriority(subzone, cross_switch) {
			if cross_subzone {
				delete(c.PriorityElements, subzone)
			}
		}
		// 匹配资源完成
		if c.PickerDone() {
			close(subzoneChan)
			return
		}
		// 非跨园区循环读取
		if !cross_subzone {
			subzoneChan <- subzone
			continue
		}
		// 跨园区
		if len(subzoneChan) == 0 {
			close(subzoneChan)
			return
		}
	}
}

// PickerMajorityElectionCrossSubzone mongo跨园区匹配
func (c *PickerObject) PickerMajorityElectionCrossSubzone() {
	sortFuncs := []func(cross_subzone bool) []string{
		c.sortSubZoneNum,
		c.sortSubZoneByPriority,
	}
	subZoneMaxCount := int(math.Ceil(float64(c.Count) / 2))
	for _, sfc := range sortFuncs {
		campKeys := sfc(true)
		if len(campKeys) == 0 {
			return
		}
		subzoneChan := make(chan subZone, len(campKeys))
		for _, v := range campKeys {
			subzoneChan <- v
		}
		for subzone := range subzoneChan {
			if len(c.PriorityElements) == 0 {
				logger.Info("go out")
				close(subzoneChan)
				return
			}
			pq, ok := c.PriorityElements[subzone]
			if !ok {
				logger.Warn("%s is queue is nil", subzone)
				delete(c.PriorityElements, subzone)
				continue
			}
			if pq.Len() == 0 {
				delete(c.PriorityElements, subzone)
			}
			logger.Info(fmt.Sprintf("surplus %s,%d", subzone, pq.Len()))
			logger.Info(fmt.Sprintf("total demand count:%d,当前满足总数有 %s:%d", c.Count, subzone, len(c.SatisfiedHostIds)))
			needCrossSwitchCheck := false
			if len(c.SatisfiedHostIdsMap[subzone]) >= 1 {
				needCrossSwitchCheck = true
			}
			if c.pickerOneByPriority(subzone, needCrossSwitchCheck) {
				if len(c.SatisfiedHostIdsMap[subzone]) >= subZoneMaxCount {
					delete(c.PriorityElements, subzone)
				}
			}
			// 匹配资源完成
			if c.PickerDone() {
				logger.Info("资源分布:%v", c.SatisfiedHostIdsMap)
				close(subzoneChan)
				return
			}
			logger.Info("subzoneChan <- %s", subzone)
			subzoneChan <- subzone
		}
	}
}

// sortSubZoneByPriority 按照SubZonePrioritySumMap的value值从大到小排序
func (c *PickerObject) sortSubZoneByPriority(cross_subzone bool) []string {
	type subZonePriority struct {
		subZone  string
		priority int64
	}
	var sorted []subZonePriority
	for subZone, priority := range c.SubZonePrioritySumMap {
		if cross_subzone && slices.Contains(c.ExistSubZone, subZone) {
			continue
		}
		sorted = append(sorted, subZonePriority{subZone, priority})
	}

	// Sort by priority in descending order
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].priority > sorted[j].priority
	})

	// Extract just the subZone names
	result := make([]string, 0, len(sorted))
	for _, item := range sorted {
		result = append(result, item.subZone)
	}

	return result
}

// sortSubZoneNum 根据排序剩下有效的园区
func (c *PickerObject) sortSubZoneNum(cross_subzone bool) []string {
	var keys []string
	var campusNice []CampusNice
	for key, pq := range c.PriorityElements {
		if pq == nil || pq.Len() == 0 {
			continue
		}
		var otherPriority int64
		if v, ok := c.SubZonePrioritySumMap[key]; ok {
			otherPriority = v
		}
		if cross_subzone {
			if cmutil.ElementNotInArry(key, c.ExistSubZone) {
				campusNice = append(campusNice, CampusNice{
					Campus: key,
					Count:  int64(pq.Len()*PriorityPMax) + otherPriority,
				})
			}
		} else {
			campusNice = append(campusNice, CampusNice{
				Campus: key,
				Count:  int64(pq.Len()*PriorityPMax) + otherPriority,
			})
		}
	}
	// 按照每个园区的数量从大到小排序
	sort.Sort(CampusWrapper{campusNice, func(p, q *CampusNice) bool {
		return q.Count < p.Count
	}})
	for _, campus := range campusNice {
		keys = append(keys, campus.Campus)
	}
	return keys
}

// pickerOneByPriority 通用的按优先级选择一台机器（兼容旧版本，不建议新代码使用）
func (c *PickerObject) pickerOneByPriority(key string, cross_switch bool) bool {
	// 根据当前配置的容忍度类型选择合适的方法
	if c.MaxPerRack > 0 {
		// 使用机架级容忍度检查（SAME_SUBZONE场景）
		return c.pickerOneByPriorityWithRackTolerance(key, cross_switch)
	}
	if c.MaxPerSubZone > 0 {
		// 使用园区级容忍度检查（CROS_SUBZONE场景）
		return c.pickerOneByPriorityWithSubZoneTolerance(key, cross_switch)
	}
	// 无容忍度限制（原有逻辑）
	return c.pickerOneByPriorityWithoutTolerance(key, cross_switch)
}

// pickerOneByPriorityWithSubZoneTolerance 带园区级容忍度检查的机器选择（用于CROS_SUBZONE）
func (c *PickerObject) pickerOneByPriorityWithSubZoneTolerance(key string, cross_switch bool) bool {
	c.ExistSubZone = append(c.ExistSubZone, key)
	pq, ok := c.PriorityElements[key]
	if !ok {
		logger.Error("not exist %s", key)
		return false
	}
	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			logger.Warn("Type Assertion failed,hostId:%s", item.Key)
			continue
		}
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				continue
			}
		}
		if slices.Contains(c.SatisfiedHostIds, v.BkHostId) {
			return false
		}

		// 园区级容忍度检查
		if c.Tolerance >= 0 && c.MaxPerSubZone > 0 {
			if !c.CanAllocateToSubZone(key) {
				logger.Debug("园区 %s 已达到容忍度限制，当前总数: %d, 最大允许: %d",
					key, c.GetSubZoneCurrentTotal(key), c.MaxPerSubZone)
				continue
			}
		}

		c.ExistRackIds = append(c.ExistRackIds, v.RackId)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistribute[key]++
		return true
	}
	return len(c.PriorityElements) == 0
}

// pickerOneByPriorityWithRackTolerance 带机架级容忍度检查的机器选择（用于SAME_SUBZONE）
func (c *PickerObject) pickerOneByPriorityWithRackTolerance(key string, cross_switch bool) bool {
	c.ExistSubZone = append(c.ExistSubZone, key)
	pq, ok := c.PriorityElements[key]
	if !ok {
		logger.Error("not exist %s", key)
		return false
	}
	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			logger.Warn("Type Assertion failed,hostId:%s", item.Key)
			continue
		}
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				continue
			}
		}
		if slices.Contains(c.SatisfiedHostIds, v.BkHostId) {
			return false
		}

		// 机架级容忍度检查
		if c.Tolerance >= 0 && c.MaxPerRack > 0 {
			if !c.CanAllocateToRack(v.RackId) {
				logger.Debug("机架 %s 已达到容忍度限制，当前总数: %d, 最大允许: %d",
					v.RackId, c.GetRackCurrentTotal(v.RackId), c.MaxPerRack)
				continue
			}
		}

		c.ExistRackIds = append(c.ExistRackIds, v.RackId)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistribute[key]++
		c.RackDistribute[v.RackId]++
		return true
	}
	return len(c.PriorityElements) == 0
}

// pickerOneByPriorityWithoutTolerance 无容忍度限制的机器选择（原有逻辑）
func (c *PickerObject) pickerOneByPriorityWithoutTolerance(key string, cross_switch bool) bool {
	c.ExistSubZone = append(c.ExistSubZone, key)
	pq, ok := c.PriorityElements[key]
	if !ok {
		logger.Error("not exist %s", key)
		return false
	}
	for pq.Len() > 0 {
		item, _ := pq.Pop()
		v, ok := item.Value.(InstanceObject)
		if !ok {
			logger.Warn("Type Assertion failed,hostId:%s", item.Key)
			continue
		}
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				continue
			}
		}
		if slices.Contains(c.SatisfiedHostIds, v.BkHostId) {
			return false
		}

		c.ExistRackIds = append(c.ExistRackIds, v.RackId)
		c.SatisfiedHostIdsMap[key] = append(c.SatisfiedHostIdsMap[key], v.BkHostId)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistribute[key]++
		return true
	}
	return len(c.PriorityElements) == 0
}

const (
	// PriorityPMax 园区count 最大
	PriorityPMax = 100000000
	// PriorityP0 priority 0
	PriorityP0 = 100000
	// PriorityP1 priority 1
	PriorityP1 = 10000
	// PriorityP2 priority 2
	PriorityP2 = 100
	// PriorityP3 priority 3
	PriorityP3 = 10
	// PriorityP4  priority 3
	PriorityP4 = 1
)

const (
	// RsRedis redis 专用资源标签
	RsRedis = "redis"
)

func (o *SearchContext) setResourcePriority(ins model.TbRpDetail, ele *Item, deviceClass string) {
	if err := ins.UnmarshalDiskInfo(); err != nil {
		logger.Error("%s unmarshal disk failed %s", ins.IP, err.Error())
	}
	// 如果请求参数请求了专属业务资源，则标记了专用业务的资源优先级更高
	if o.IntentionBkBizId > 0 && ins.DedicatedBiz == o.IntentionBkBizId {
		ele.Priority += PriorityP0
	}
	// 如果请求的磁盘为空，尽量匹配没有磁盘的机器
	// 请求参数需要几块盘，如果机器盘数量预制相等，则优先级更高
	if len(o.StorageSpecs) == len(ins.Storages) {
		ele.Priority += PriorityP1
	}
	// 如果请求参数包含规格，如果机器机型匹配,则高优先级
	if len(o.DeviceClass) > 0 && lo.Contains(o.DeviceClass, ins.DeviceClass) {
		ele.Priority += PriorityP2
	}
	if ins.DeviceClass == deviceClass {
		ele.Priority += PriorityP2
	}
	// 当请求参数请求了磁盘,则匹配磁盘大小相近的机器优先级更高
	if len(o.StorageSpecs) > 0 {
		storageSpecMap := lo.SliceToMap(o.StorageSpecs, func(item meta.DiskSpec) (string, meta.DiskSpec) {
			return item.MountPoint, item
		})
		var scores []int64
		var weights []float64
		for mp, disk := range ins.Storages {
			if spec, ok := storageSpecMap[mp]; ok {
				// 已经匹配到的资源，磁盘一定是大于等于请求的磁盘最小的值的
				// 倾向匹配磁盘小的机器
				scores = append(scores, int64((1-float32(disk.Size-spec.MinSize)/float32(disk.Size))*PriorityP2))
				weights = append(weights, 1/float64(len(ins.Storages)))
			}
		}
		if len(scores) > 0 {
			ele.Priority += weightedScore(scores, weights)
		}
	} else {
		if len(ins.Storages) == 0 {
			ele.Priority += PriorityP2
		} else {
			var scores []int64
			var weights []float64
			// 如果请求参数没有磁盘规格，尽量匹配没有磁盘的机器
			for _, disk := range ins.Storages {
				// 已经匹配到的资源，磁盘一定是大于等于请求的磁盘最小的值的
				// 倾向匹配磁盘小的机器
				scores = append(scores, 10000000-int64(disk.Size))
				weights = append(weights, 1/float64(len(ins.Storages))*0.00001)
			}
			if len(scores) > 0 {
				ele.Priority += weightedScore(scores, weights)
			}
		}
	}
	//  如果请求参数请求了专属db类型，机器的资源类型标签只有一个，且等于请求的资源的类中，则优先级更高
	if lo.IsNotEmpty(o.RsType) && (ins.RsType == o.RsType) {
		ele.Priority += PriorityP2
	}
	// 如果是匹配的资源是redis资源
	// 在内存满足的条件下，偏向取cpu核心小的机器
	if lo.Contains([]string{RsRedis}, o.RsType) {
		ele.Priority += int64((1.0 - float32(ins.CPUNum-o.Spec.Cpu.Min)/float32(ins.CPUNum)) * PriorityP2)
	}
	// 根据资源的导入的时间create_time,导入时间越早，优先级越高
	// create_time 字段类型是 timestamp
	if !ins.CreateTime.IsZero() {
		// 计算时间差（单位：小时），时间越早，hoursSinceCreation越大
		hoursSinceCreation := time.Since(ins.CreateTime).Hours()
		// 限制时间差不超过一年
		if hoursSinceCreation > 365*24 {
			hoursSinceCreation = 365 * 24
		}
		// 优先级与时间差成正比，时间越早，优先级越高
		ele.Priority += int64((hoursSinceCreation / (365 * 24)) * 50)
	}
}

// weightedScore 加权评分
func weightedScore(scores []int64, weights []float64) int64 {
	if len(scores) != len(weights) {
		panic("评分与权重数量不匹配")
	}
	var total float64
	for i := range scores {
		total += float64(scores[i]) * weights[i]
	}
	return int64(total)
}

// AnalysisResourcePriority 分析资源的优先级
func (o *SearchContext) AnalysisResourcePriority(insList []model.TbRpDetail, israndom bool) (map[string]*PriorityQueue,
	map[string]int64,
	error) {
	result := make(map[string]*PriorityQueue)
	maxMumDeviceClass := getMaxNumDeviceClass(insList)
	subZonePrioritySumMap := make(map[string]int64)
	netDeviceIdPrioritySumMap := make(map[string]int64)
	itemsMap := make(map[string][]Item)
	for _, ins := range insList {
		netDeviceIdPrioritySumMap[ins.NetDeviceID]++
	}
	for _, ins := range insList {
		ele := Item{
			Key:      strconv.Itoa(ins.BkHostID),
			Priority: 1,
			Value: InstanceObject{
				BkHostId:        ins.BkHostID,
				RackId:          ins.RackID,
				LinkNetdeviceId: strings.Split(ins.NetDeviceID, ","),
				Nice:            createNice(int(ins.CPUNum), ins.DramCap, 0, 0),
				InsDetail:       &ins,
			},
		}
		o.setResourcePriority(ins, &ele, maxMumDeviceClass)
		if israndom {
			itemsMap[RANDOM] = append(itemsMap[RANDOM], ele)
		} else {
			if slices.Contains([]string{SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH}, o.Affinity) {
				v, ok := netDeviceIdPrioritySumMap[ins.NetDeviceID]
				if !ok {
					v = 0
				}
				ele.Priority += v * PriorityP2
			}
			itemsMap[ins.SubZone] = append(itemsMap[ins.SubZone], ele)
			subZonePrioritySumMap[ins.SubZone] += ele.Priority
		}
	}
	logger.Debug("items map %v", itemsMap)
	for subZoneName, items := range itemsMap {
		// init priority queue
		if _, exist := result[subZoneName]; !exist {
			result[subZoneName] = NewPriorityQueue()
		}
		for _, item := range items {
			if err := result[subZoneName].Push(&item); err != nil {
				// 安全日志：打印重复键与队列键，便于定位异常数据
				logger.Error("push item failed %v, subZone=%s, key=%s, priority=%d",
					err, subZoneName, item.Key, item.Priority)
				return nil, subZonePrioritySumMap, err
			}
		}
	}
	logger.Info("sub zone priority sum map %v", subZonePrioritySumMap)
	return result, subZonePrioritySumMap, nil
}

// getMaxNumDeviceClass 获取机型数量最多的机型
func getMaxNumDeviceClass(items []model.TbRpDetail) string {
	maxNum := 0
	maxType := ""
	dclCountMap := make(map[string]int)
	for _, item := range items {
		dclCountMap[item.DeviceClass]++
		if dclCountMap[item.DeviceClass] > maxNum {
			maxNum = dclCountMap[item.DeviceClass]
			maxType = item.DeviceClass
		}
	}
	return maxType
}
