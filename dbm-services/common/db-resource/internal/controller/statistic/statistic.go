/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package statistic 资源统计相关接口
package statistic

import (
	"errors"
	"fmt"
	"hash/crc32"
	"math"
	"sort"
	"strconv"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

// Handler statistic handler
type Handler struct {
	controller.BaseHandler
}

const (
	// EmptyDeviceClass 无机型信息
	EmptyDeviceClass = "无机型信息"
)

// RegisterRouter 注册路由
func (s *Handler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("statistic")
	{
		r.POST("/groupby/resource_type", s.CountGroupbyResourceType)
		r.POST("/summary", s.ResourceDistribution)
	}
}

// CountGroupbyResourceType 按照资源类型统计

// CountGroupbyResourceTypeResult 按照资源类型统计结果数据
type CountGroupbyResourceTypeResult struct {
	RsType string `json:"rs_type"`
	Count  int    `json:"count"`
}

// CountGroupbyResourceType count groupby resource type
func (s *Handler) CountGroupbyResourceType(c *gin.Context) {
	var data []CountGroupbyResourceTypeResult
	err := model.DB.Self.Table(model.TbRpDetailName()).
		Select("rs_type, count(*) as count").Group("rs_type").
		Find(&data, "status = ? ", model.Unused).Error
	if err != nil {
		logger.Error("query failed %s", err.Error)
		s.SendResponse(c, err, err.Error(), "")
	}
	s.SendResponse(c, nil, data, "")
}

// ResourDistributionParam 统计资源分布参数
type ResourDistributionParam struct {
	ForBiz         int          `json:"for_biz"`
	City           string       `json:"city"`
	SubZoneIds     []string     `json:"subzone_ids"`
	GroupBy        string       `json:"group_by" binding:"required"`
	SpecParam      DbmSpecParam `json:"spec_param" `
	SetBizEmpty    bool         `json:"set_empty_biz"`
	SetRsTypeEmpty bool         `json:"set_empty_resource_type"`
}

// DbmSpecParam 规格参数
type DbmSpecParam struct {
	DbType      string `json:"db_type"`
	MachineType string `json:"machine_type"`
	ClusterType string `json:"cluster_type"`
	SpecIdList  []int  `json:"spec_id_list"`
}

func (m DbmSpecParam) getQueryParam() map[string]string {
	p := make(map[string]string)
	if lo.IsNotEmpty(m.DbType) && m.DbType != model.PUBLIC_RESOURCE_DBTYEP {
		p["spec_db_type"] = m.DbType
	}
	if lo.IsNotEmpty(m.MachineType) {
		p["spec_machine_type"] = m.MachineType
	}
	if lo.IsNotEmpty(m.ClusterType) {
		p["spec_cluster_type"] = m.ClusterType
	}
	if len(m.SpecIdList) > 0 {
		var specIdStrList []string
		for _, specId := range m.SpecIdList {
			specIdStrList = append(specIdStrList, strconv.Itoa(specId))
		}
		p["spec_ids"] = strings.Join(specIdStrList, ",")
	}
	return p
}

// ResourceDistribution 统计资源分布
func (s *Handler) ResourceDistribution(c *gin.Context) {
	var param ResourDistributionParam
	if err := s.Prepare(c, &param); err != nil {
		logger.Error("parse ResourDistributionParam failed: %v", err)
		s.SendResponse(c, err, "Failed to parse parameters", "")
		return
	}

	dbmClient := dbmapi.NewDbmClient()
	specList, err := dbmClient.GetDbmSpec(param.SpecParam.getQueryParam())
	if err != nil {
		logger.Error("get dbm spec failed: %v", err)
		s.SendResponse(c, err, "Failed to get DBM specifications", "")
		return
	}
	allLogicCityInfos, err := dbmapi.GetAllLogicCityInfo()
	if err != nil {
		logger.Error("get all logic city info failed: %v", err)
		s.SendResponse(c, err, "Failed to get logic city info", "")
		return
	}
	cityMap := make(map[string]string)
	for _, cityInfo := range allLogicCityInfos {
		cityMap[cityInfo.BkIdcCityName] = cityInfo.LogicalCityName
	}
	db := model.DB.Self.Table(model.TbRpDetailName())
	if err := param.dbFilter(db); err != nil {
		s.SendResponse(c, err, "Failed to apply database filter", "")
		return
	}

	var rsListBefore, rsList []model.TbRpDetail
	if err := db.Find(&rsListBefore).Error; err != nil {
		logger.Error("query failed: %v", err)
		s.SendResponse(c, err, "Failed to query resource list", "")
		return
	}
	for _, rs := range rsListBefore {
		if v, ok := cityMap[rs.City]; ok {
			rs.City = v
		}
		rsList = append(rsList, rs)
	}
	var result interface{}
	var processErr error

	switch param.GroupBy {
	case "device_class":
		result = s.processDeviceClassGroup(rsList, specList, param.SpecParam.ClusterType)
	case "spec":
		result, processErr = groupByDbmSpec(rsList, specList)
	default:
		err := errors.New("unknown aggregation type")
		msg := fmt.Sprintf("Unknown aggregation type: %s", param.GroupBy)
		s.SendResponse(c, err, msg, "")
		return
	}

	if processErr != nil {
		s.SendResponse(c, processErr, "Failed to process data", "")
		return
	}

	s.SendResponse(c, nil, result, "")
}

func (s *Handler) processDeviceClassGroup(
	rsList []model.TbRpDetail,
	specList []dbmapi.DbmSpec,
	clusterType string,
) interface{} {
	if lo.IsEmpty(clusterType) {
		return groupByDeviceClass(rsList)
	}

	var filteredList []model.TbRpDetail
	for _, rs := range rsList {
		for _, spec := range specList {
			if rs.MatchDbmSpec(spec) {
				filteredList = append(filteredList, rs)
				break
			}
		}
	}
	return groupByDeviceClass(filteredList)
}

func (r ResourDistributionParam) dbFilter(db *gorm.DB) (err error) {
	db.Where("status = ? ", model.Unused)
	if lo.IsNotEmpty(r.City) {
		realCitys, err := dbmapi.GetIdcCityByLogicCity(r.City)
		if err != nil {
			logger.Error("get idc city by logic city failed %s", err.Error())
			return fmt.Errorf("根据逻辑城市%s获取机房城市失败:%v", r.City, err)
		}
		db.Where("city in (?)", realCitys)
	}
	if len(r.SubZoneIds) > 0 {
		db.Where("sub_zone_id in (?)", r.SubZoneIds)
	}
	if !r.SetBizEmpty {
		db.Where("dedicated_biz = ? ", r.ForBiz)
	}
	if !r.SetRsTypeEmpty {
		db.Where("rs_type  = ?", r.SpecParam.DbType)
	}
	return nil
}

func dealCity(city string) string {
	// if lo.IsEmpty(city) {
	// 	city = "无区域信息"
	// }
	return city
}

func dealDeviceClass(deviceClass string) string {
	if lo.IsEmpty(deviceClass) {
		deviceClass = EmptyDeviceClass
	}
	return deviceClass
}

// CityGroupCount city分组统计
type CityGroupCount struct {
	City  string
	Count int
}

// GroupByDeviceClassResult 按照机型聚合结果
type GroupByDeviceClassResult struct {
	DedicatedBiz  int                    `json:"dedicated_biz"`
	City          string                 `json:"city"`
	DeviceClass   string                 `json:"device_class"`
	DiskSummary   []bk.DiskInfo          `json:"disk_summary"`
	CpuMemSummary string                 `json:"cpu_mem_summary"`
	Count         int                    `json:"count"`
	SubZoneDetail map[string]SubZoneInfo `json:"sub_zone_detail"`
}

func groupByDeviceClass(rpList []model.TbRpDetail) []GroupByDeviceClassResult {
	groupMap := make(map[string]*GroupByDeviceClassResult)
	cityCountMap := make(map[string]int)

	for _, rs := range rpList {
		if err := rs.UnmarshalDiskInfo(); err != nil {
			logger.Error("%s: unmarshal disk info failed %s", rs.IP, err.Error())
			continue
		}

		diskHash32 := crc32.ChecksumIEEE([]byte(rs.ConcatDiskInfoIgnoreDiskId()))
		city := dealCity(rs.City)
		deviceClass := dealDeviceClass(rs.DeviceClass)
		groupKey := fmt.Sprintf("%d:%s:%s:%d", rs.DedicatedBiz, city, deviceClass, diskHash32)

		group, exists := groupMap[groupKey]
		if !exists {
			group = &GroupByDeviceClassResult{
				DedicatedBiz:  rs.DedicatedBiz,
				City:          city,
				DeviceClass:   deviceClass,
				DiskSummary:   make([]bk.DiskInfo, 0),
				SubZoneDetail: make(map[string]SubZoneInfo),
			}
			groupMap[groupKey] = group
		}

		group.Count++
		cityCountMap[city]++

		if len(group.DiskSummary) == 0 {
			for mp, dinfo := range rs.Storages {
				group.DiskSummary = append(group.DiskSummary, bk.DiskInfo{
					MountPoint: mp,
					DiskDetail: bk.DiskDetail{
						Size:     dinfo.Size,
						DiskType: dinfo.DiskType,
					},
				})
			}
		}

		if group.CpuMemSummary == "" && lo.IsNotEmpty(rs.DeviceClass) {
			group.CpuMemSummary = fmt.Sprintf("%d核%dG", rs.CPUNum, int(math.Ceil(float64(rs.DramCap)/1000)))
		}

		subZoneInfo := group.SubZoneDetail[rs.SubZoneID]
		subZoneInfo.Name = rs.SubZone
		subZoneInfo.Count++
		group.SubZoneDetail[rs.SubZoneID] = subZoneInfo
	}

	var citysGroupKey []CityGroupCount
	for city, count := range cityCountMap {
		citysGroupKey = append(citysGroupKey, CityGroupCount{City: city, Count: count})
	}

	sort.SliceStable(citysGroupKey, func(i, j int) bool {
		return citysGroupKey[i].Count > citysGroupKey[j].Count
	})

	result := make([]GroupByDeviceClassResult, 0, len(groupMap))
	for _, cityGroup := range citysGroupKey {
		cityResults := make([]GroupByDeviceClassResult, 0)
		for _, group := range groupMap {
			if group.City == cityGroup.City {
				cityResults = append(cityResults, *group)
			}
		}
		sort.SliceStable(cityResults, func(i, j int) bool {
			return cityResults[i].Count > cityResults[j].Count
		})
		result = append(result, cityResults...)
	}

	return result
}

// GroupBySpecResult 按照规格聚合结果
type GroupBySpecResult struct {
	DedicatedBiz    int                    `json:"dedicated_biz"`
	City            string                 `json:"city"`
	SpecId          int                    `json:"spec_id"`
	SpecName        string                 `json:"spec_name"`
	SpecMachineType string                 `json:"spec_machine_type"`
	SpecClusterType string                 `json:"spec_cluster_type"`
	Count           int                    `json:"count"`
	SubZoneDetail   map[string]SubZoneInfo `json:"sub_zone_detail"`
}

// SubZoneInfo sub zone count info
type SubZoneInfo struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

func transferSubZoneDetail(subZonegroupMap map[string]int, subZoneMap map[string]string) map[string]SubZoneInfo {
	s := make(map[string]SubZoneInfo)
	for subZoneId, count := range subZonegroupMap {
		subName := ""
		if v, ok := subZoneMap[subZoneId]; ok {
			subName = v
		}
		s[subZoneId] = SubZoneInfo{
			Count: count,
			Name:  subName,
		}
	}
	return s
}

func groupByDbmSpec(rpList []model.TbRpDetail, specList []dbmapi.DbmSpec) (result []GroupBySpecResult, err error) {
	result = []GroupBySpecResult{}
	specMap := make(map[int]dbmapi.DbmSpec)
	for _, spec := range specList {
		specMap[spec.SpecId] = spec
	}
	specMatchrelationMap := rsMatchSpecs(rpList, specList)
	groupMap := make(map[string][]model.TbRpDetail)
	subZonegroupMap := make(map[string]map[string]int)
	subzoneNameMap := make(map[string]string)
	for _, rs := range rpList {
		matchSpecIds, ok := specMatchrelationMap[rs.BkHostID]
		if !ok {
			logger.Warn("%s 资源没有匹配到任何规格", rs.IP)
			continue
		}
		subzoneNameMap[rs.SubZoneID] = rs.SubZone
		for _, specId := range matchSpecIds {
			groupKey := fmt.Sprintf("%d:%s:%d", rs.DedicatedBiz, dealCity(rs.City), specId)
			groupMap[groupKey] = append(groupMap[groupKey], rs)
			if _, exist := subZonegroupMap[groupKey]; !exist {
				subZonegroupMap[groupKey] = make(map[string]int)
				subZonegroupMap[groupKey][rs.SubZoneID] = 1
			} else {
				subZonegroupMap[groupKey][rs.SubZoneID]++
			}
		}
	}
	cityMap := make(map[string][]GroupBySpecResult)
	cityCountMap := make(map[string]int)
	for groupKey, grs := range groupMap {
		dedicatedBiz, city, specId, err := parseSpecGroupKey(groupKey)
		if err != nil {
			logger.Error("parse group key failed %s", err.Error)
			continue
		}
		spec, ok := specMap[specId]
		if !ok {
			spec = dbmapi.DbmSpec{}
		}

		cityCountMap[city] += len(grs)
		cityMap[city] = append(cityMap[city], GroupBySpecResult{
			DedicatedBiz:    dedicatedBiz,
			SpecId:          specId,
			SpecName:        spec.SpecName,
			SpecMachineType: spec.SpecMachineType,
			SpecClusterType: spec.SpecClusterType,
			City:            city,
			Count:           len(grs),
			SubZoneDetail:   transferSubZoneDetail(subZonegroupMap[groupKey], subzoneNameMap),
		})
	}
	var citysGroupKey []CityGroupCount
	for city, count := range cityCountMap {
		citysGroupKey = append(citysGroupKey, CityGroupCount{City: city, Count: count})
	}
	// 对城市整体数量进行排序
	sort.SliceStable(citysGroupKey, func(i, j int) bool {
		return citysGroupKey[i].Count > citysGroupKey[j].Count
	})
	// 按照subZone数量排序
	for _, city := range citysGroupKey {
		part := cityMap[city.City]
		sort.SliceStable(part, func(i, j int) bool {
			return part[i].Count > part[j].Count
		})
		result = append(result, part...)
	}
	return result, nil
}

func parseSpecGroupKey(groupKey string) (dedicatedBiz int, city string, specId int, err error) {
	cols := strings.Split(groupKey, ":")
	if len(cols) < 3 {
		return -1, "", -1, fmt.Errorf("group key format error, %s", groupKey)
	}
	dedicatedBiz, err = strconv.Atoi(cols[0])
	if err != nil {
		return -1, "", -1, fmt.Errorf("dedicated biz format error, %s", cols[0])
	}
	city = cols[1]
	specId, err = strconv.Atoi(cols[2])
	return dedicatedBiz, city, specId, err
}

func rsMatchSpecs(rsList []model.TbRpDetail, specList []dbmapi.DbmSpec) map[int][]int {
	relationMap := make(map[int][]int)
	ctrlChan := make(chan struct{}, 10)
	wg := sync.WaitGroup{}
	lc := sync.Mutex{}
	for _, rs := range rsList {
		for _, spec := range specList {
			wg.Add(1)
			ctrlChan <- struct{}{}
			go func(xrs model.TbRpDetail, xspec dbmapi.DbmSpec) {
				if xrs.MatchDbmSpec(xspec) {
					lc.Lock()
					relationMap[xrs.BkHostID] = append(relationMap[xrs.BkHostID], xspec.SpecId)
					lc.Unlock()
				}
				wg.Done()
				<-ctrlChan
			}(rs, spec)
		}
	}
	wg.Wait()
	return relationMap
}
