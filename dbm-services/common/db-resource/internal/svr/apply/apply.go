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
	"gorm.io/gorm/clause"
)

// SearchContext TODO
type SearchContext struct {
	*ObjectDetail
	RsType          string
	IntetionBkBizId int
	IdcCitys        []string
}

// CycleApply 循环匹配
func CycleApply(param RequestInputParam) (pickers []*PickerObject, err error) {
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
		var idcCitys []string
		if config.AppConfig.RunMode == "dev" {
			idcCitys = []string{}
		} else if cmutil.ElementNotInArry(v.Affinity, []string{CROSS_RACK, NONE}) || lo.IsNotEmpty(&v.LocationSpec.City) {
			idcCitys, err = dbmapi.GetIdcCityByLogicCity(v.LocationSpec.City)
			if err != nil {
				logger.Error("request real citys by logic city %s from bkdbm api failed:%v", v.LocationSpec.City, err)
				return pickers, err
			}
		}

		s := &SearchContext{
			IntetionBkBizId: param.ForbizId,
			RsType:          param.ResourceType,
			ObjectDetail:    &v,
			IdcCitys:        idcCitys,
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

// RollBackAllInstanceUnused 将 Instance Status  Selling  ==> Not Selled : 2 --> 0
func RollBackAllInstanceUnused(ms []*PickerObject) {
	for _, m := range ms {
		if err := m.RollbackUnusedInstance(); err != nil {
			logger.Error(fmt.Sprintf("Rollback Satisfied Instance Status NotSelled Failed,Error %s", err.Error()))
		}
	}
}

func (o *SearchContext) pickBase(db *gorm.DB) {
	db.Where("gse_agent_status_code = ? ", bk.GSE_AGENT_OK)
	if o.BkCloudId <= 0 {
		db.Where(" bk_cloud_id = ? and status = ?  ", o.ObjectDetail.BkCloudId, model.Unused)
	} else {
		db.Where(" bk_cloud_id = ? and status = ?  ", o.BkCloudId, model.Unused)
	}
	// os type
	// Windows
	// Liunx
	osType := o.ObjectDetail.OsType
	if cmutil.IsEmpty(o.ObjectDetail.OsType) {
		osType = "Linux"
	}
	db.Where("os_type = ? ", osType)

	// match os name  like  Windows Server 2012
	if len(o.ObjectDetail.OsNames) > 0 {
		conditions := []clause.Expression{}
		for _, osname := range o.ObjectDetail.OsNames {
			conditions = append(conditions, clause.Like{
				Column: "os_name",
				Value:  "%" + strings.TrimSpace(strings.ToLower(osname)) + "%",
			})
		}
		if len(conditions) == 1 {
			db.Clauses(clause.AndConditions{Exprs: conditions})
		} else {
			// 有多个条件，使用or，才会被用（）包括起来所有的or条件
			db.Clauses(clause.OrConditions{Exprs: conditions})
		}
	}

	// 如果没有指定资源类型，表示只能选择无资源类型标签的资源
	// 没有资源类型标签的资源可以被所有其他类型使用
	if lo.IsEmpty(o.RsType) {
		db.Where("rs_type == 'PUBLIC' ")
	} else {
		db.Where("rs_type in (?)", []string{"PUBLIC", o.RsType})
	}
	// 如果没有指定专属业务，就表示只能选用公共的资源
	// 不能匹配打了业务标签的资源
	if o.IntetionBkBizId <= 0 {
		db.Where("dedicated_biz == 0")
	} else {
		db.Where("dedicated_biz in (?)", []int{0, o.IntetionBkBizId})
	}
	o.MatchLables(db)
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
	db := model.DB.Self.Table(model.TbRpDetailName()).Select("count(*)")
	o.pickBase(db)
	if err := db.Scan(&count).Error; err != nil {
		logger.Error("query pre check count failed %s", err.Error())
		return errno.ErrDBQuery.AddErr(err)
	}

	if int(count) < o.Count {
		return errno.ErrResourceinsufficient.AddErr(fmt.Errorf("申请需求:%s\n\r资源池符合条件的资源总数:%d 小于申请的数量", o.GetMessage(),
			count))
	}
	return nil
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
	if len(diskSpecs) > 0 {
		ts := []model.TbRpDetail{}
		for _, ins := range items {
			if err = ins.UnmarshalDiskInfo(); err != nil {
				logger.Error("%s umarshal disk failed %s", ins.IP, err.Error())
				return picker, err
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
			return picker, errno.ErrResourceinsufficient.Add(fmt.Sprintf("匹配磁盘%s,的资源为 0", o.GetDiskMatchInfo()))
		}
		items = ts
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

// MatchLables match lables
func (o *SearchContext) MatchLables(db *gorm.DB) {
	if len(o.Labels) > 0 {
		for key, v := range o.Labels {
			db.Where(" ( json_contains(label,json_object(?,?) )", key, v)
		}
		return
	}
	db.Where(" JSON_TYPE(label) = 'NULL' OR JSON_LENGTH(label) <= 1 ")
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
	logger.Info("spec %v", s)
	logger.Info("detail %v", d)
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

// PickInstanceBase TODO
func (o *SearchContext) PickInstanceBase(picker *PickerObject, items []model.TbRpDetail) (err error) {
	logger.Info("the anti-affinity is %s", o.Affinity)
	switch o.Affinity {
	case NONE:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, true)
		picker.PickerRandom()
	case CROS_SUBZONE:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, false)
		picker.PickerCrossSubzone(true)
	case MAX_EACH_ZONE_EQUAL:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, false)
		picker.PickerCrossSubzone(false)
	case SAME_SUBZONE:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(false)
	case SAME_SUBZONE_CROSS_SWTICH:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(true)
	case CROSS_RACK:
		picker.PriorityElements, err = o.AnalysisResourcePriority(items, true)
		picker.PickerSameSubZone(true)
	}
	return
}

// MatchLocationSpec 匹配location参数
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
		return
	}
	if o.LocationSpec.IncludeOrExclude {
		db.Where("sub_zone_id in ?", o.LocationSpec.SubZoneIds)
	} else {
		db.Where("sub_zone_id  not in ?", o.LocationSpec.SubZoneIds)
	}
}

// MatchStorage  匹配存储参数
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

func isWindowsPath(path string) bool {
	return strings.Contains(path, "\\")
}

// MatchSpec TODO
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
