/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package apply TODO
package apply

import (
	"fmt"
	"path"
	"slices"
	"sort"
	"strings"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/samber/lo"
	"gorm.io/gorm"
)

// SearchContext TODO
type SearchContext struct {
	*ObjectDetail
	RsType            string
	IntetionBkBizId   int
	IdcCitys          []string
	SpecialSubZoneIds []string
	SpecialHostIds    []int
}

// applyGroupsInSameLocaltion apply groups in same location
func applyGroupsInSameLocaltion(param RequestInputParam) (pickers []*PickerObject, err error) {
	var picker *PickerObject
	resourceReqList, err := param.SortDetails()
	if err != nil {
		logger.Error("对请求参数排序失败%v", err)
		return nil, err
	}
	var idcCitys []string
	v := resourceReqList[0]
	idcCitys, err = getLogicIdcCitys(v)
	if err != nil {
		logger.Error("get logic citys failed %s", err.Error())
		return pickers, err
	}
	var subzoneIds []string
	specialSubZoneIds, isExclude := param.SpecialSubZoneIds()
	// 如果有指定的子园区，那么就按照指定的子园区进行分配
	if !isExclude && len(specialSubZoneIds) > 0 {
		subzoneIds = specialSubZoneIds
	} else {
		// 根据请求，按照请求的分组，分别计算出每个分组的匹配的园区的优先级
		groupcampusNice, errx := getGroupcampusNice(param, resourceReqList, idcCitys)
		if errx != nil {
			logger.Error("order campus nice failed %s", errx.Error())
			return pickers, errx
		}
		// 因为整个大的分组在需要分配机器在同一个园区，这里合并所有的分组的园区优先级
		// 合并之后再次排序，返回整体的园区优先级
		nsubzoneIds := sortgroupcampusNice(groupcampusNice)
		// 如果需要排除指定的子园区，那么就排除指定的子园区
		if isExclude && len(specialSubZoneIds) > 0 {
			subzoneIds, _ = lo.Difference(nsubzoneIds, specialSubZoneIds)
		} else {
			subzoneIds = nsubzoneIds
		}
	}
	logger.Info("sort subzone ids %v", subzoneIds)
	if len(subzoneIds) == 0 {
		return pickers, errno.ErrResourceinsufficient.Add("没有符合条件的资源")
	}
	for _, subzoneId := range subzoneIds {
		pickers = []*PickerObject{}
		for _, v := range resourceReqList {
			s := &SearchContext{
				IntetionBkBizId:   param.ForbizId,
				RsType:            param.ResourceType,
				ObjectDetail:      &v,
				IdcCitys:          idcCitys,
				SpecialHostIds:    v.Hosts.GetBkHostIds(),
				SpecialSubZoneIds: []string{subzoneId},
			}
			if err = s.PickCheck(); err != nil {
				logger.Error("挑选资源失败:%v", err)
				goto RollBack
			}
			// 挑选符合需求的资源
			picker, err = s.PickInstance()
			if err != nil {
				logger.Error("挑选资源失败:%v", err)
				goto RollBack
			}
			// Debug Print Log 挑选实例分区的情况
			picker.DebugDistrubuteLog()
			// 更新挑选到的资源的状态为Preselected
			if updateErr := picker.PreselectedSatisfiedInstance(); updateErr != nil {
				goto RollBack
			}
			// 追加到挑选好的分组
			pickers = append(pickers, picker)
		}
		return pickers, nil
	RollBack:
		RollBackAllInstanceUnused(pickers)
	}
	return pickers, err
}
func getGroupcampusNice(param RequestInputParam, resourceReqList []ObjectDetail,
	idcCitys []string) (groupcampusNice map[string]map[string]*SubZoneSummary,
	err error) {
	groupcampusNice = make(map[string]map[string]*SubZoneSummary)
	for _, v := range resourceReqList {
		s := &SearchContext{
			IntetionBkBizId: param.ForbizId,
			RsType:          param.ResourceType,
			ObjectDetail:    &v,
			IdcCitys:        idcCitys,
			SpecialHostIds:  v.Hosts.GetBkHostIds(),
		}
		var items []model.TbRpDetail
		db := model.DB.Self.Table(model.TbRpDetailName())
		s.pickBase(db)
		if err = db.Scan(&items).Error; err != nil {
			logger.Error("query failed %s", err.Error())
			return nil, errno.ErrDBQuery.AddErr(err)
		}
		campusSummarys := make(map[string]*SubZoneSummary)
		for _, item := range items {
			if _, ok := campusSummarys[item.SubZoneID]; !ok {
				campusSummarys[item.SubZoneID] = &SubZoneSummary{
					Count:             1,
					EquipmentIdList:   []string{item.RackID},
					LinkNetdeviceList: strings.Split(item.NetDeviceID, ","),
					RequestCount:      v.Count,
				}
			} else {
				campusSummarys[item.SubZoneID].Count++
				campusSummarys[item.SubZoneID].EquipmentIdList = append(campusSummarys[item.SubZoneID].EquipmentIdList, item.RackID)
				campusSummarys[item.SubZoneID].LinkNetdeviceList = append(campusSummarys[item.SubZoneID].LinkNetdeviceList,
					strings.Split(item.NetDeviceID, ",")...)
			}
		}
		groupcampusNice[v.GroupMark] = campusSummarys
	}
	return groupcampusNice, nil
}

func sortgroupcampusNice(gpms map[string]map[string]*SubZoneSummary) []string {
	subzones := []string{}
	gcnsMap := make(map[string]*CampusNice)
	var cns []CampusNice
	for _, campuseSummary := range gpms {
		for campus := range campuseSummary {
			equipmentIdList := lo.Uniq(campuseSummary[campus].EquipmentIdList)
			linkNetdeviceList := lo.Uniq(campuseSummary[campus].LinkNetdeviceList)
			count := campuseSummary[campus].Count
			requestCount := campuseSummary[campus].RequestCount
			if count >= requestCount && len(equipmentIdList) >= requestCount &&
				len(linkNetdeviceList) >= requestCount {
				cns = append(cns, CampusNice{
					Campus: campus,
					Count:  int64(count + len(equipmentIdList)*(1+PriorityP3) + len(linkNetdeviceList)*(PriorityP3+1)),
				})
			}
		}
	}

	for _, cn := range cns {
		if _, ok := gcnsMap[cn.Campus]; !ok {
			gcnsMap[cn.Campus] = &CampusNice{
				Campus: cn.Campus,
				Count:  cn.Count,
			}
		} else {
			gcnsMap[cn.Campus].Count += cn.Count
		}
	}
	var gcns []CampusNice
	for key := range gcnsMap {
		gcns = append(gcns, CampusNice{
			Campus: key,
			Count:  gcnsMap[key].Count,
		})
	}
	sort.Sort(CampusWrapper{gcns, func(p, q *CampusNice) bool {
		return q.Count < p.Count
	}})

	for _, v := range gcns {
		subzones = append(subzones, v.Campus)
	}
	return subzones
}

// SubZoneSummary subzone summary
type SubZoneSummary struct {
	RequestCount      int
	Count             int
	EquipmentIdList   []string // 存在的设备Id
	LinkNetdeviceList []string // 存在的网卡Id
}

func getLogicIdcCitys(v ObjectDetail) (idcCitys []string, err error) {
	if config.AppConfig.RunMode == "dev" {
		idcCitys = []string{}
	} else if cmutil.ElementNotInArry(v.Affinity, []string{CROSS_RACK, NONE}) ||
		lo.IsNotEmpty(v.LocationSpec.City) ||
		len(v.Hosts) > 0 {
		idcCitys, err = dbmapi.GetIdcCityByLogicCity(v.LocationSpec.City)
		if err != nil {
			logger.Error("request real citys by logic city %s from bkdbm api failed:%v", v.LocationSpec.City, err)
			return []string{}, err
		}
	}
	return idcCitys, nil
}

// CycleApply 循环匹配
func CycleApply(param RequestInputParam) (pickers []*PickerObject, err error) {
	// 多个请求参数分组在同一个地方
	affinitys := lo.Uniq(param.GetAllAffinitys())
	if param.GroupsInSameLocation && len(param.Details) > 1 && len(affinitys) == 1 &&
		slices.Contains([]string{SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH}, affinitys[0]) {
		logger.Info("apply all groups in same location")
		return applyGroupsInSameLocaltion(param)
	}
	resourceReqList, err := param.SortDetails()
	if err != nil {
		logger.Error("对请求参数排序失败%v", err)
		return nil, err
	}
	for _, v := range resourceReqList {
		var picker *PickerObject
		logger.Debug(fmt.Sprintf("input.Detail %v", v))
		// 如果没有配置亲和性，或者请求的数量小于1 重置亲和性为NONE
		if v.Affinity == "" || v.Count <= 1 {
			v.Affinity = NONE
		}
		idcCitys, err := getLogicIdcCitys(v)
		if err != nil {
			logger.Error("get logic citys failed %s", err.Error())
			return pickers, err
		}
		s := &SearchContext{
			IntetionBkBizId: param.ForbizId,
			RsType:          param.ResourceType,
			ObjectDetail:    &v,
			IdcCitys:        idcCitys,
			SpecialHostIds:  v.Hosts.GetBkHostIds(),
		}
		if err = s.PickCheck(); err != nil {
			return pickers, err
		}
		// 挑选符合需求的资源
		picker, err = s.PickInstance()
		if err != nil {
			return pickers, err
		}
		// Debug Print Log 挑选实例分区的情况
		picker.DebugDistrubuteLog()
		// 更新挑选到的资源的状态为Preselected
		if updateErr := picker.PreselectedSatisfiedInstance(); updateErr != nil {
			return pickers, fmt.Errorf("update %s Picker Out Satisfied Instance Status In Selling Failed:%v", v.GroupMark,
				updateErr.Error())
		}
		// 追加到挑选好的分组
		pickers = append(pickers, picker)
	}
	return pickers, nil
}

// RollBackAllInstanceUnused reserve all instance unused
func RollBackAllInstanceUnused(ms []*PickerObject) {
	for _, m := range ms {
		if err := m.RollbackUnusedInstance(); err != nil {
			logger.Error(fmt.Sprintf("Rollback Satisfied Instance Status NotSelled Failed,Error %s", err.Error()))
		}
	}
}

func (o *SearchContext) pickBase(db *gorm.DB) {
	// 如果指定了特殊资源，就只查询这些资源
	if len(o.SpecialHostIds) > 0 {
		db.Where("bk_host_id in (?) and status = ? and gse_agent_status_code = ? ", o.SpecialHostIds, model.Unused,
			bk.GSE_AGENT_OK)
		return
	}
	db.Where("bk_cloud_id = ? and status = ? and gse_agent_status_code = ? ", o.BkCloudId, model.Unused, bk.GSE_AGENT_OK)

	o.MatchIntetionBkBiz(db)
	o.MatchRsType(db)
	o.MatchOsType(db)
	o.MatchOsName(db)
	o.MatchLabels(db)
	o.MatchLocationSpec(db)
	o.MatchStorage(db)
	o.MatchSpec(db)
	switch o.Affinity {
	// 如果需要存在跨园区检查则需要判断是否存在网卡id,机架id等
	case SAME_SUBZONE_CROSS_SWTICH:
		o.UseNetDeviceIsNotEmpty(db)
	case CROSS_RACK:
		o.RackIdIsNotEmpty(db)
	}
}

// PickCheck precheck
func (o *SearchContext) PickCheck() (err error) {
	var count int64
	logger.Info("前置检查轮资源匹配")
	if len(o.SpecialHostIds) > 0 {
		return o.PickCheckSpecialBkhostIds()
	}
	db := model.DB.Self.Table(model.TbRpDetailName()).Select("count(*)")
	o.pickBase(db)
	if err := db.Scan(&count).Error; err != nil {
		logger.Error("query pre check count failed %s", err.Error())
		return errno.ErrDBQuery.AddErr(err)
	}

	if int(count) < o.Count {
		return fmt.Errorf("申请需求:%s\n\r资源池符合条件的资源总数:%d 小于申请的数量", o.GetMessage(), count)
	}
	return nil
}

// PickCheckSpecialBkhostIds 根据bkhostids取资源
func (o *SearchContext) PickCheckSpecialBkhostIds() (err error) {
	var rs []int
	err = model.DB.Self.Table(model.TbRpDetailName()).Select("bk_host_id").Where(
		"bk_host_id in (?) and status = ? and bk_cloud_id = ? ",
		o.SpecialHostIds, model.Unused, o.BkCloudId).Scan(&rs).Error
	if err != nil {
		logger.Error("query pre check count failed %s", err.Error())
		return errno.ErrDBQuery.AddErr(err)
	}
	if len(rs) != len(o.SpecialHostIds) {
		emptyIps := []string{}
		hostIpMap := lo.SliceToMap(o.Hosts, func(item Host) (int, string) { return item.BkHostId, item.IP })
		for hostid, ip := range hostIpMap {
			if !lo.Contains(rs, hostid) {
				emptyIps = append(emptyIps, ip)
			}
		}
		return fmt.Errorf("指定ip申请资源,部分资源不存在:%v", emptyIps)
	}
	return nil
}

// filterEmptyMountPointStorage 过滤没有挂载点的磁盘匹配需求
func (o *SearchContext) filterEmptyMountPointStorage(items []model.TbRpDetail,
	diskSpecs []meta.DiskSpec) (ts []model.TbRpDetail, err error) {
	for _, ins := range items {
		if err = ins.UnmarshalDiskInfo(); err != nil {
			logger.Error("%s umarshal disk failed %s", ins.IP, err.Error())
			return nil, err
		}
		logger.Info("%v", ins.Storages)
		noUseStorages := make(map[string]bk.DiskDetail)
		smp := meta.GetDiskSpecMountPoints(o.StorageSpecs)
		for mp, v := range ins.Storages {
			if cmutil.ElementNotInArry(mp, smp) {
				noUseStorages[mp] = v
			}
		}
		logger.Info("nouse: %v", noUseStorages)
		if matchNoMountPointStorage(diskSpecs, noUseStorages) {
			ts = append(ts, ins)
		}
	}
	if len(ts) == 0 {
		return nil, errno.ErrResourceinsufficient.Add(fmt.Sprintf("匹配磁盘%s,的资源为 0", o.GetDiskMatchInfo()))
	}
	return ts, nil
}

// PickInstance match resource
func (o *SearchContext) PickInstance() (picker *PickerObject, err error) {
	picker = NewPicker(o.Count, o.GroupMark)
	var items []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName())
	o.pickBase(db)
	if err = db.Scan(&items).Error; err != nil {
		logger.Error("query failed %s", err.Error())
		return nil, errno.ErrDBQuery.AddErr(err)
	}
	// 过滤没有挂载点的磁盘匹配需求
	logger.Info("storage spec %v", o.StorageSpecs)

	diskSpecs := meta.GetEmptyDiskSpec(o.StorageSpecs)
	if len(diskSpecs) > 0 && len(o.SpecialHostIds) == 0 {
		items, err = o.filterEmptyMountPointStorage(items, diskSpecs)
		if err != nil {
			logger.Error("filter empty mount point storage failed %s", err.Error())
			return picker, err
		}
	}

	if err = o.PickInstanceBase(picker, items); err != nil {
		return nil, err
	}

	if picker.PickerDone() {
		return picker, nil
	}

	return nil, errno.ErrResourceinsufficient.Add(fmt.Sprintf("Picker for %s, 所有资源无法满足 %s的参数需求", o.GroupMark,
		o.GetMessage()))
}

// PickInstanceBase pick instance base
func (o *SearchContext) PickInstanceBase(picker *PickerObject, items []model.TbRpDetail) (err error) {
	logger.Info("the anti-affinity is %s", o.Affinity)
	if len(o.SpecialHostIds) > 0 {
		for _, v := range items {
			picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostID)
		}
		picker.Count = len(o.SpecialHostIds)
		return nil
	}
	switch o.Affinity {
	case NONE:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, true)
		picker.PickerRandom()
	case CROS_SUBZONE:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerCrossSubzone(true)
	case MAX_EACH_ZONE_EQUAL:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerCrossSubzone(false)
	case SAME_SUBZONE:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(false)
	case SAME_SUBZONE_CROSS_SWTICH:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(true)
	case CROSS_RACK:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, true)
		picker.PickerSameSubZone(true)
	}
	return
}

// MatchIntetionBkBiz match intetion biz
func (o *SearchContext) MatchIntetionBkBiz(db *gorm.DB) {
	// 如果没有指定专属业务，就表示只能选用公共的资源
	// 不能匹配打了业务标签的资源
	if o.IntetionBkBizId <= 0 {
		db.Where("dedicated_biz = 0")
	} else {
		db.Where("dedicated_biz in (?)", []int{0, o.IntetionBkBizId})
	}
}

// MatchRsType pick rs type
func (o *SearchContext) MatchRsType(db *gorm.DB) {
	// 如果没有指定资源类型，表示只能选择无资源类型标签的资源
	// 没有资源类型标签的资源可以被所有其他类型使用
	if lo.IsEmpty(o.RsType) {
		db.Where("rs_type = 'PUBLIC' ")
	} else {
		db.Where("rs_type in (?)", []string{"PUBLIC", o.RsType})
	}
}

// MatchOsType match os type
func (o *SearchContext) MatchOsType(db *gorm.DB) {
	// os type: Windows, Liunx
	osType := o.ObjectDetail.OsType
	if cmutil.IsEmpty(o.ObjectDetail.OsType) {
		osType = model.LiunxOs
	}
	db.Where("os_type = ? ", osType)
}

// MatchOsName match os name os_name = "tlinux-1.2"
func (o *SearchContext) MatchOsName(db *gorm.DB) {
	// match os name  like  Windows Server 2012
	// conditions := []clause.Expression{}
	// for _, osname := range o.ObjectDetail.OsNames {
	// 	conditions = append(conditions, clause.Like{
	// 		Column: "os_name",
	// 		Value:  "%" + strings.TrimSpace(strings.ToLower(osname)) + "%",
	// 	})
	// }
	// if len(conditions) == 1 {
	// 	db.Clauses(clause.AndConditions{Exprs: conditions})
	// } else {
	// 	// 有多个条件，使用or，才会被用（）包括起来所有的or条件
	// 	db.Clauses(clause.OrConditions{Exprs: conditions})
	// }
	if len(o.ObjectDetail.OsNames) == 0 {
		return
	}
	if o.ObjectDetail.ExcludeOsName {
		db.Where("os_name not in (?)", o.ObjectDetail.OsNames)
	} else {
		db.Where("os_name in (?)", o.ObjectDetail.OsNames)
	}
}

// MatchLabels match labels
func (o *SearchContext) MatchLabels(db *gorm.DB) {
	if len(o.Labels) > 0 {
		db.Where(model.JSONQuery("labels").JointOrContains(o.Labels))
	} else {
		// 如果请求没有标签, 只能匹配没有标签的资源
		db.Where(" JSON_TYPE(labels) = 'NULL' or JSON_TYPE(labels) is null OR JSON_LENGTH(labels) < 1 ")
	}
}

// MatchLocationSpec match location parameter
func (o *SearchContext) MatchLocationSpec(db *gorm.DB) {
	if o.LocationSpec.IsEmpty() {
		return
	}
	logger.Info("get real city is %v", o.IdcCitys)
	if len(o.IdcCitys) > 0 {
		db = db.Where("city in ? ", o.IdcCitys)
	} else {
		db = db.Where("city = ? ", o.LocationSpec.City)
	}
	if o.LocationSpec.SubZoneIsEmpty() {
		if len(o.SpecialSubZoneIds) > 0 {
			db.Where("sub_zone_id in (?)", o.SpecialSubZoneIds)
		}
		return
	}
	if o.LocationSpec.IsExclude() {
		db.Where("sub_zone_id not in (?)", o.LocationSpec.SubZoneIds)
	} else {
		db.Where("sub_zone_id in (?)", o.LocationSpec.SubZoneIds)
	}
}

// MatchStorage  match storage parameters
func (o *SearchContext) MatchStorage(db *gorm.DB) {
	if len(o.StorageSpecs) == 0 {
		return
	}
	for _, d := range o.StorageSpecs {
		if lo.IsEmpty(d.MountPoint) {
			continue
		}
		mp := path.Clean(d.MountPoint)
		if isWindowsPath(mp) {
			mp = strings.ReplaceAll(mp, `\`, ``)
		}
		if cmutil.IsNotEmpty(d.DiskType) {
			db.Where(model.JSONQuery("storage_device").Equals(d.DiskType, mp, "disk_type"))
		}
		logger.Info("storage spec is %v", d)
		switch {
		case d.MaxSize > 0:
			db.Where(model.JSONQuery("storage_device").NumRange(d.MinSize, d.MaxSize, mp, "size"))
		case d.MaxSize <= 0 && d.MinSize > 0:
			db.Where(model.JSONQuery("storage_device").Gte(d.MinSize, mp, "size"))
		}
	}
}

// MatchSpec match spec
func (o *SearchContext) MatchSpec(db *gorm.DB) {
	if len(o.DeviceClass) > 0 {
		switch {
		case o.Spec.Cpu.IsEmpty() && o.Spec.Mem.IsEmpty():
			db.Where(" device_class in (?) ", o.DeviceClass)
		case o.Spec.Cpu.IsEmpty() && o.Spec.Mem.IsNotEmpty():
			db.Where("? or device_class in (?)", o.Spec.Mem.MatchMemBuilder(), o.DeviceClass)
		case o.Spec.Cpu.IsNotEmpty() && o.Spec.Mem.IsEmpty():
			db.Where("? or device_class in (?)", o.Spec.Cpu.MatchCpuBuilder(), o.DeviceClass)
		case o.Spec.Cpu.IsNotEmpty() && o.Spec.Mem.IsNotEmpty():
			db.Where("( ? and  ? ) or device_class in (?)", o.Spec.Cpu.MatchCpuBuilder(), o.Spec.Mem.MatchMemBuilder(),
				o.DeviceClass)
		}
		return
	}
	o.Spec.Cpu.MatchCpu(db)
	o.Spec.Mem.MatchMem(db)
}

// UseNetDeviceIsNotEmpty filster net device id not empty
func (o *SearchContext) UseNetDeviceIsNotEmpty(db *gorm.DB) {
	db.Where("(net_device_id  is not null and net_device_id != '') and (rack_id is not null and rack_id != '')")
}

// RackIdIsNotEmpty filter rackid is not empty
func (o *SearchContext) RackIdIsNotEmpty(db *gorm.DB) {
	db.Where("rack_id is not null and rack_id != ''")
}

func isWindowsPath(path string) bool {
	return strings.Contains(path, "\\")
}

func matchNoMountPointStorage(spec []meta.DiskSpec, sinc map[string]bk.DiskDetail) bool {
	mcount := 0
	for _, s := range spec {
		for mp, d := range sinc {
			if diskDetailMatch(d, s) {
				delete(sinc, mp)
				mcount++
				break
			}
		}
	}
	return mcount == len(spec)
}

func diskDetailMatch(d bk.DiskDetail, s meta.DiskSpec) bool {
	if d.DiskType != s.DiskType && cmutil.IsNotEmpty(s.DiskType) {
		logger.Info("disk type not match")
		return false
	}
	if d.Size > s.MaxSize && s.MaxSize > 0 {
		logger.Info("max size not match")
		return false
	}
	if d.Size < s.MinSize {
		logger.Info("min size not match")
		return false
	}
	return true
}
