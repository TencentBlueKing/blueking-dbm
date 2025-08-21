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
		c.ExistEquipmentIds = []string{}
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

// PickerCrossSubzone 跨园区匹配
func (c *PickerObject) PickerCrossSubzone(cross_subzone, cross_switch bool) {
	sortFuncs := []func(cross_subzone bool) []string{
		c.sortSubZoneByPriority,
		c.sortSubZoneNum,
	}
	for _, sfc := range sortFuncs {
		campKeys := sfc(cross_subzone)
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
			if len(sfc(cross_subzone)) == 0 {
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

func (c *PickerObject) pickerOneByPriority(key string, cross_switch bool) bool {
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
		c.ExistEquipmentIds = append(c.ExistEquipmentIds, v.Equipment)
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
				Equipment:       ins.RackID,
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
	logger.Info("items map %v", itemsMap)
	for subZoneName, items := range itemsMap {
		// init priority queue
		if _, exist := result[subZoneName]; !exist {
			result[subZoneName] = NewPriorityQueue()
		}
		for _, item := range items {
			if err := result[subZoneName].Push(&item); err != nil {
				logger.Error("push item failed %v", err)
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
