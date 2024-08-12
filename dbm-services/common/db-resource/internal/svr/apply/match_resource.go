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
	"sort"
	"strconv"
	"strings"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
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
		logger.Info("dbeug %v", subzone)
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
func (c *PickerObject) PickerCrossSubzone(cross_subzone bool) {
	campKeys := c.sortSubZoneNum(cross_subzone)
	if len(campKeys) == 0 {
		return
	}
	subzoneChan := make(chan subzone, len(campKeys))
	for _, v := range campKeys {
		subzoneChan <- v
	}
	for subzone := range subzoneChan {
		pq, ok := c.PriorityElements[subzone]
		if !ok {
			logger.Warn("%s is queue is nil", subzone)
			continue
		}
		if pq.Len() == 0 {
			delete(c.PriorityElements, subzone)
		}
		if len(c.sortSubZoneNum(cross_subzone)) == 0 {
			logger.Info("go out here")
			close(subzoneChan)
			return
		}
		logger.Info(fmt.Sprintf("surplus %s,%d", subzone, pq.Len()))
		logger.Info(fmt.Sprintf("%s,%d,%d", subzone, c.Count, len(c.SatisfiedHostIds)))
		if c.pickerOneByPriority(subzone, false) {
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

// sortSubZoneNum 根据排序剩下有效的园区
func (c *PickerObject) sortSubZoneNum(cross_subzone bool) []string {
	var keys []string
	var campusNice []CampusNice
	for key, pq := range c.PriorityElements {
		if pq == nil || pq.Len() == 0 {
			continue
		}
		if cross_subzone {
			if cmutil.ElementNotInArry(key, c.ExistSubZone) {
				campusNice = append(campusNice, CampusNice{
					Campus: key,
					Count:  pq.Len(),
				})
			}
		} else {
			campusNice = append(campusNice, CampusNice{
				Campus: key,
				Count:  pq.Len(),
			})
		}
	}
	// 按照每个园区的数量从大到小排序
	sort.Sort(CampusWrapper{campusNice, func(p, q *CampusNice) bool {
		return q.Count < p.Count
	}})
	for _, capmus := range campusNice {
		keys = append(keys, capmus.Campus)
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
			logger.Warn("Type Assertion faild,hostId:%s", item.Key)
			continue
		}
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				continue
			}
		}
		c.ExistEquipmentIds = append(c.ExistEquipmentIds, v.Equipment)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.SelectedResources = append(c.SelectedResources, v.InsDetail)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistrbute[key]++
		return true
	}
	return len(c.PriorityElements) == 0
}

const (
	// PriorityP0 TODO
	PriorityP0 = 100000
	// PriorityP1 TODO
	PriorityP1 = 10000
	// PriorityP2 TODO
	PriorityP2 = 1000
	// PriorityP3 TODO
	PriorityP3 = 100
	// PriorityP4 TODO
	PriorityP4 = 10
)

const (
	// RsRedis redis 专用资源标签
	RsRedis = "redis"
)

func (o *SearchContext) setResourcePriority(ins model.TbRpDetail, ele *Item) {

	logger.Info("%v", ins.Storages)
	if err := ins.UnmarshalDiskInfo(); err != nil {
		logger.Error("%s umarshal disk failed %s", ins.IP, err.Error())
	}

	// 如果请求的磁盘为空，尽量匹配没有磁盘的机器
	// 请求参数需要几块盘，如果机器盘数量预制相等，则优先级更高
	if len(o.StorageSpecs) == len(ins.Storages) {
		ele.Priority += PriorityP0
	}
	// 如果请求参数包含规格，如果机器机型匹配,则高优先级
	if len(o.DeviceClass) > 0 && lo.Contains(o.DeviceClass, ins.DeviceClass) {
		ele.Priority += PriorityP1
	}
	// 如果请求参数请求了专属业务资源，则标记了专用业务的资源优先级更高
	if o.IntetionBkBizId > 0 && ins.DedicatedBiz == o.IntetionBkBizId {
		ele.Priority += PriorityP2
	}

	//  如果请求参数请求了专属db类型，机器的资源类型标签只有一个，且等于请求的资源的类中，则优先级更高
	if lo.IsNotEmpty(o.RsType) && (ins.RsType == o.RsType) {
		ele.Priority += PriorityP2
	}
	// 如果是匹配的资源是redis资源
	// 在内存满足的条件下，偏向取cpu核心小的机器
	if lo.Contains([]string{RsRedis}, o.RsType) {
		ele.Priority += int64((1.0 - float32(ins.CPUNum-o.Spec.Cpu.Min)/float32(ins.CPUNum)) * PriorityP3)
	}
}

// AnalysisResourcePriority 分析资源的优先级
func (o *SearchContext) AnalysisResourcePriority(insList []model.TbRpDetail, israndom bool) (map[string]*PriorityQueue,
	error) {
	result := make(map[string]*PriorityQueue)
	itemsMap := make(map[string][]Item)
	for _, ins := range insList {
		ele := Item{
			Key:      strconv.Itoa(ins.BkHostID),
			Priority: 0,
			Value: InstanceObject{
				BkHostId:        ins.BkHostID,
				Equipment:       ins.RackID,
				LinkNetdeviceId: strings.Split(ins.NetDeviceID, ","),
				Nice:            createNice(int(ins.CPUNum), ins.DramCap, 0, 0),
				InsDetail:       &ins,
			},
		}
		o.setResourcePriority(ins, &ele)
		if israndom {
			itemsMap[RANDOM] = append(itemsMap[RANDOM], ele)
		} else {
			itemsMap[ins.SubZone] = append(itemsMap[ins.SubZone], ele)
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
				return nil, err
			}
		}
	}
	return result, nil
}
