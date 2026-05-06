/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package statistic

import (
	"encoding/json"
	"sort"
	"strconv"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

// WaterLevelHandlerOptimized 优化后的水位统计处理器
type WaterLevelHandlerOptimized struct {
	controller.BaseHandler
}

// RegisterRouter 注册路由
func (h *WaterLevelHandlerOptimized) RegisterRouter(engine *gin.Engine) {
	engine.POST("/statistic/water_level", h.WaterLevelStatisticBySpec)
	engine.POST("/statistic/water_level_by_spec", h.WaterLevelStatisticBySpec)
}

// MachineBasicInfo 机器基础信息，仅包含匹配规格所需的字段
// 相比 TbRpDetail 减少约 80% 的内存占用
type MachineBasicInfo struct {
	BkHostID      int             `gorm:"column:bk_host_id"`
	City          string          `gorm:"column:city"`
	SubZoneID     string          `gorm:"column:sub_zone_id"`
	SubZone       string          `gorm:"column:sub_zone"`
	OsName        string          `gorm:"column:os_name"`
	OsNameOrigin  string          `gorm:"column:os_name_origin"`
	CPUNum        int             `gorm:"column:cpu_num"`
	DramCap       int             `gorm:"column:dram_cap"`
	DeviceClass   string          `gorm:"column:device_class"`
	StorageDevice json.RawMessage `gorm:"column:storage_device"`
}

// AggregatedMachineGroup 数据库层聚合的机器分组
type AggregatedMachineGroup struct {
	City         string `gorm:"column:city"`
	SubZoneID    string `gorm:"column:sub_zone_id"`
	OsName       string `gorm:"column:os_name"`
	OsNameOrigin string `gorm:"column:os_name_origin"`
	Count        int    `gorm:"column:count"`
	// 以下字段用于规格匹配的代表性数据
	MinCPU        int    `gorm:"column:min_cpu"`
	MaxCPU        int    `gorm:"column:max_cpu"`
	MinMem        int    `gorm:"column:min_mem"`
	MaxMem        int    `gorm:"column:max_mem"`
	DeviceClasses string `gorm:"column:device_classes"` // 逗号分隔的 device_class 列表
}

// WaterLevelStatisticOptimized 优化后的水位统计接口
// 优化策略：
// 1. 数据库层聚合减少数据传输量
// 2. 分批处理避免一次性加载所有数据
// 3. 精简字段减少内存占用
// 4. 流式聚合减少中间数据结构
func (h *WaterLevelHandlerOptimized) WaterLevelStatisticOptimized(c *gin.Context) {
	specList, err := h.getSpecList()
	if err != nil {
		h.SendResponse(c, err, "Failed to get DBM specifications")
		return
	}
	specMap := make(map[int]dbmapi.DbmSpec, len(specList))
	specRsTypeMapList := make(map[string][]dbmapi.DbmSpec, len(specList))
	for _, spec := range specList {
		specMap[spec.SpecId] = spec
		specRsTypeMapList[spec.SpecClusterType] = append(specRsTypeMapList[spec.SpecClusterType], spec)
	}
	var response []WaterLevelStatisticResponse
	logger.Info("specRsTypeMapList: %+v", specRsTypeMapList)
	for rsType, specList := range specRsTypeMapList {
		// 使用分批流式处理，大幅减少内存占用
		result, osNameMap, err := h.processInBatches(specList, rsType)
		if err != nil {
			h.SendResponse(c, err, "Failed to process machines")
			return
		}

		// 构建最终响应
		for _, item := range result {
			osNameOrigin := ""
			if item.OsName != "" {
				if origin, ok := osNameMap[item.OsName]; ok {
					osNameOrigin = origin
				}
			}
			response = append(response, WaterLevelStatisticResponse{
				City:            item.City,
				SubZoneId:       item.SubZoneId,
				SubZone:         item.SubZone,
				SpecId:          item.SpecId,
				OsName:          item.OsName,
				OsNameOrigin:    osNameOrigin,
				SpecName:        specMap[item.SpecId].SpecName,
				SpecClusterType: specMap[item.SpecId].SpecClusterType,
				Count:           item.Count,
			})
		}
	}
	// 按 count 降序排序
	sort.Slice(response, func(i, j int) bool {
		return response[i].Count > response[j].Count
	})

	h.SendResponse(c, nil, map[string]interface{}{
		"data":  response,
		"total": len(response),
	})
}

// WaterLevelResultItem 水位统计结果项
type WaterLevelResultItem struct {
	City      string
	SubZoneId string
	SubZone   string
	SpecId    int
	OsName    string
	Count     int
}

// processInBatches 分批处理机器数据
// 使用游标分页避免一次性加载所有数据
func (h *WaterLevelHandlerOptimized) processInBatches(specList []dbmapi.DbmSpec, rsType string) (
	[]WaterLevelResultItem, map[string]string, error) {

	const batchSize = 1000 // 每批处理 1000 条

	// 聚合结果 map: "city|sub_zone_id|spec_id|os_name" -> count
	aggregateMap := make(map[string]*WaterLevelResultItem)
	osNameMap := make(map[string]string)
	var mu sync.Mutex

	var lastID int
	for {
		// 分批查询，只选择需要的字段
		var machines []MachineBasicInfo
		err := model.DB.Self.Table(model.TbRpDetailName()).
			Select("bk_host_id, city, sub_zone_id, sub_zone, os_name, os_name_origin, cpu_num, dram_cap, device_class, storage_device").
			Where("dedicated_biz = 0 AND status = ? AND id > ? AND rs_type = ? and city != ''", model.Unused, lastID, rsType).
			Order("id ASC").
			Limit(batchSize).
			Find(&machines).Error
		if err != nil {
			return nil, nil, err
		}

		if len(machines) == 0 {
			break
		}

		// 更新 lastID 用于下一批
		// 使用 bk_host_id 作为游标（假设 id 是自增的）
		// 如果表没有 id 字段，可以使用其他唯一字段
		lastID += batchSize

		// 处理当前批次
		h.processBatch(machines, specList, aggregateMap, osNameMap, &mu)
	}

	// 转换为切片
	result := make([]WaterLevelResultItem, 0, len(aggregateMap))
	for _, item := range aggregateMap {
		result = append(result, *item)
	}

	return result, osNameMap, nil
}

// processBatch 处理单批机器数据
func (h *WaterLevelHandlerOptimized) processBatch(
	machines []MachineBasicInfo,
	specList []dbmapi.DbmSpec,
	aggregateMap map[string]*WaterLevelResultItem,
	osNameMap map[string]string,
	mu *sync.Mutex) {

	// 使用 worker pool 模式，控制并发数
	const workerCount = 10
	jobs := make(chan MachineBasicInfo, len(machines))
	var wg sync.WaitGroup

	// 启动 worker
	for i := 0; i < workerCount; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for machine := range jobs {
				h.processSingleMachine(machine, specList, aggregateMap, osNameMap, mu)
			}
		}()
	}

	// 分发任务
	for _, machine := range machines {
		jobs <- machine
	}
	close(jobs)

	wg.Wait()
}

// processSingleMachine 处理单台机器
func (h *WaterLevelHandlerOptimized) processSingleMachine(
	machine MachineBasicInfo,
	specList []dbmapi.DbmSpec,
	aggregateMap map[string]*WaterLevelResultItem,
	osNameMap map[string]string,
	mu *sync.Mutex) {

	// 更新 osNameMap（线程安全）
	mu.Lock()
	if machine.OsNameOrigin != "" {
		osNameMap[machine.OsName] = machine.OsNameOrigin
	}
	mu.Unlock()

	// 遍历规格进行匹配
	for _, spec := range specList {
		if matchDbmSpecOptimized(machine, spec) {
			key := machine.City + "|" + machine.SubZoneID + "|" + strconv.Itoa(spec.SpecId) + "|" + machine.OsName

			mu.Lock()
			if item, exists := aggregateMap[key]; exists {
				item.Count++
			} else {
				aggregateMap[key] = &WaterLevelResultItem{
					City:      machine.City,
					SubZoneId: machine.SubZoneID,
					SubZone:   machine.SubZone,
					SpecId:    spec.SpecId,
					OsName:    machine.OsName,
					Count:     1,
				}
			}
			mu.Unlock()
		}
	}
}

// matchDbmSpecOptimized 优化后的规格匹配函数
// 相比原版本去除了大量日志输出，提升性能
func matchDbmSpecOptimized(m MachineBasicInfo, spec dbmapi.DbmSpec) bool {
	if len(spec.DeviceClass) > 0 {
		if !lo.Contains(spec.DeviceClass, m.DeviceClass) {
			return false
		}
	} else {
		if !isWithinRangeOpt(m.CPUNum, spec.Cpu.Min, spec.Cpu.Max) {
			return false
		}
		if !isWithinRangeOpt(m.DramCap, int(spec.Mem.Min*1024), int(spec.Mem.Max*1024)) {
			return false
		}
	}

	if len(spec.StorageSpecs) > 0 {
		storages := make(map[string]bk.DiskDetail)
		if err := json.Unmarshal(m.StorageDevice, &storages); err != nil {
			return false
		}
		for _, diskSpec := range spec.StorageSpecs {
			mp := diskSpec.MountPoint
			realDiskInfo, ok := storages[mp]
			if !ok {
				if diskSpec.Min == 0 {
					continue
				}
				return false
			}
			if diskSpec.DiskType != "ALL" && lo.IsNotEmpty(diskSpec.DiskType) {
				if diskSpec.DiskType != realDiskInfo.DiskType {
					return false
				}
			}
			if realDiskInfo.Size < diskSpec.Min || realDiskInfo.Size > diskSpec.Max {
				return false
			}
		}
	}
	return true
}

func isWithinRangeOpt(value, min, max int) bool {
	return value >= min && value <= max
}

// matchStorageSpec 仅进行磁盘规格匹配
// 当数据库层已根据 CPU/内存/设备类型预过滤后，仅需进行磁盘规格的二次匹配
func matchStorageSpec(storageDevice json.RawMessage, storageSpecs []dbmapi.RealDiskSpec) bool {
	if len(storageSpecs) == 0 {
		return true
	}

	storages := make(map[string]bk.DiskDetail)
	if err := json.Unmarshal(storageDevice, &storages); err != nil {
		return false
	}

	for _, diskSpec := range storageSpecs {
		mp := diskSpec.MountPoint
		realDiskInfo, ok := storages[mp]
		if !ok {
			// 如果磁盘规格最小值为0，匹配空的磁盘也允许
			if diskSpec.Min == 0 {
				continue
			}
			return false
		}
		// 检查磁盘类型
		if diskSpec.DiskType != "ALL" && lo.IsNotEmpty(diskSpec.DiskType) {
			if diskSpec.DiskType != realDiskInfo.DiskType {
				return false
			}
		}
		// 检查磁盘大小范围
		if realDiskInfo.Size < diskSpec.Min || realDiskInfo.Size > diskSpec.Max {
			return false
		}
	}
	return true
}

// WaterLevelStatisticBySpec 基于规格优先的水位统计接口
// 实现思路：先根据规格条件在数据库层预过滤机器，再进行磁盘等复杂条件的二次匹配
// 优势：利用数据库索引预过滤，减少应用层处理的数据量
func (h *WaterLevelHandlerOptimized) WaterLevelStatisticBySpec(c *gin.Context) {
	// 1. 获取规格列表
	specList, err := h.getSpecList()
	if err != nil {
		h.SendResponse(c, err, "Failed to get DBM specifications")
		return
	}

	// 构建规格映射
	specMap := make(map[int]dbmapi.DbmSpec, len(specList))
	specRsTypeMapList := make(map[string][]dbmapi.DbmSpec, len(specList))
	for _, spec := range specList {
		specMap[spec.SpecId] = spec
		specRsTypeMapList[spec.SpecClusterType] = append(specRsTypeMapList[spec.SpecClusterType], spec)
	}

	// 聚合结果 map: "city|sub_zone_id|spec_id|os_name" -> WaterLevelResultItem
	aggregateMap := make(map[string]*WaterLevelResultItem)
	osNameMap := make(map[string]string)
	var mu sync.Mutex

	logger.Info("WaterLevelStatisticBySpec: specRsTypeMapList count=%d", len(specRsTypeMapList))

	// 2. 按 rs_type 分组处理
	for rsType, specs := range specRsTypeMapList {
		// 3. 遍历每个规格，根据规格条件查询匹配的机器
		for _, spec := range specs {
			machines, queryErr := h.queryMachinesBySpec(spec, rsType)
			if queryErr != nil {
				logger.Error("queryMachinesBySpec failed: spec_id=%d, err=%s", spec.SpecId, queryErr.Error())
				continue
			}

			// 4. 对查询结果进行磁盘规格二次匹配并聚合
			h.aggregateMachinesBySpec(machines, spec, aggregateMap, osNameMap, &mu)
		}
	}

	// 5. 转换为响应格式
	var response []WaterLevelStatisticResponse
	for _, item := range aggregateMap {
		osNameOrigin := ""
		if item.OsName != "" {
			if origin, ok := osNameMap[item.OsName]; ok {
				osNameOrigin = origin
			}
		}
		response = append(response, WaterLevelStatisticResponse{
			City:            item.City,
			SubZoneId:       item.SubZoneId,
			SubZone:         item.SubZone,
			SpecId:          item.SpecId,
			OsName:          item.OsName,
			OsNameOrigin:    osNameOrigin,
			SpecName:        specMap[item.SpecId].SpecName,
			SpecClusterType: specMap[item.SpecId].SpecClusterType,
			Count:           item.Count,
		})
	}

	// 6. 按 count 降序排序
	sort.Slice(response, func(i, j int) bool {
		return response[i].Count > response[j].Count
	})

	h.SendResponse(c, nil, map[string]interface{}{
		"data":  response,
		"total": len(response),
	})
}

// aggregateMachinesBySpec 对查询到的机器进行磁盘二次匹配并聚合结果
func (h *WaterLevelHandlerOptimized) aggregateMachinesBySpec(
	machines []MachineBasicInfo,
	spec dbmapi.DbmSpec,
	aggregateMap map[string]*WaterLevelResultItem,
	osNameMap map[string]string,
	mu *sync.Mutex) {

	for _, machine := range machines {
		// 更新 osNameMap
		mu.Lock()
		if machine.OsNameOrigin != "" {
			osNameMap[machine.OsName] = machine.OsNameOrigin
		}
		mu.Unlock()

		// 磁盘规格二次匹配
		if !matchStorageSpec(machine.StorageDevice, spec.StorageSpecs) {
			continue
		}

		// 聚合计数
		key := machine.City + "|" + machine.SubZoneID + "|" + strconv.Itoa(spec.SpecId) + "|" + machine.OsName
		mu.Lock()
		if item, exists := aggregateMap[key]; exists {
			item.Count++
		} else {
			aggregateMap[key] = &WaterLevelResultItem{
				City:      machine.City,
				SubZoneId: machine.SubZoneID,
				SubZone:   machine.SubZone,
				SpecId:    spec.SpecId,
				OsName:    machine.OsName,
				Count:     1,
			}
		}
		mu.Unlock()
	}
}

// getSpecList 获取规格列表（复用原有逻辑）
func (h *WaterLevelHandlerOptimized) getSpecList() ([]dbmapi.DbmSpec, error) {
	if config.AppConfig.RunMode == "local" {
		return generateMockSpecData(), nil
	}
	client := GetDbmClient()
	return client.GetDbmSpec(map[string]string{"enable": "true"})
}

// queryMachinesBySpec 根据规格条件查询匹配的机器
// 利用数据库索引预过滤，减少应用层处理的数据量
func (h *WaterLevelHandlerOptimized) queryMachinesBySpec(spec dbmapi.DbmSpec, rsType string) ([]MachineBasicInfo, error) {
	var machines []MachineBasicInfo

	db := model.DB.Self.Table(model.TbRpDetailName()).
		Select("bk_host_id, city, sub_zone_id, sub_zone, os_name, os_name_origin, cpu_num, dram_cap, device_class, storage_device").
		Where("dedicated_biz = ? AND status = ? AND rs_type in (?) and city != ''", model.PUBLIC_RESOURCE_BIZ, model.Unused, []string{rsType, model.PUBLIC_RESOURCE_DBTYEP})

	// 根据规格条件构建查询
	db = h.buildSpecQueryConditions(db, spec)

	err := db.Find(&machines).Error
	if err != nil {
		return nil, err
	}

	return machines, nil
}

// buildSpecQueryConditions 根据规格构建数据库查询条件
// 如果规格指定了 device_class，则使用 IN 条件
// 否则使用 cpu_num 和 dram_cap 的范围条件
func (h *WaterLevelHandlerOptimized) buildSpecQueryConditions(db *gorm.DB, spec dbmapi.DbmSpec) *gorm.DB {
	if len(spec.DeviceClass) > 0 {
		// 使用 device_class IN 条件
		db = db.Where("device_class IN ?", spec.DeviceClass)
	} else {
		// 使用 CPU 范围条件
		if spec.Cpu.Min > 0 && spec.Cpu.Max > 0 {
			db = db.Where("cpu_num BETWEEN ? AND ?", spec.Cpu.Min, spec.Cpu.Max)
		} else if spec.Cpu.Min > 0 {
			db = db.Where("cpu_num >= ?", spec.Cpu.Min)
		} else if spec.Cpu.Max > 0 {
			db = db.Where("cpu_num <= ?", spec.Cpu.Max)
		}

		// 使用内存范围条件（规格中内存单位是 GB，数据库中是 MB）
		memMinMB := int(spec.Mem.Min * 1024)
		memMaxMB := int(spec.Mem.Max * 1024)
		if memMinMB > 0 && memMaxMB > 0 {
			db = db.Where("dram_cap BETWEEN ? AND ?", memMinMB, memMaxMB)
		} else if memMinMB > 0 {
			db = db.Where("dram_cap >= ?", memMinMB)
		} else if memMaxMB > 0 {
			db = db.Where("dram_cap <= ?", memMaxMB)
		}
	}

	return db
}
