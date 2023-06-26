// Package apply TODO
package apply

import (
	"fmt"
	"path"
	"strconv"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/gorm"
)

// SearchContext TODO
type SearchContext struct {
	*ApplyObjectDetail
	BkCloudId       int
	RsType          string
	IntetionBkBizId int
	IdcCitys        []string
}

func getRealCitys(logicCity string) (realCitys []string, err error) {
	if cmutil.IsEmpty(logicCity) {
		return
	}
	err = model.CMDBDB.Self.Raw(
		"select distinct bk_idc_city_name from db_meta_bkcity where  logical_city_id in (select id from db_meta_logicalcity  where name = ?  ) ",
		logicCity).Scan(&realCitys).Error
	if err != nil {
		logger.Error("from region %s find real city failed %s", logicCity, err.Error())
		return
	}
	return
}

// CycleApply TODO
func CycleApply(param ApplyRequestInputParam) (pickers []*PickerObject, err error) {
	for _, v := range param.Details {
		var picker *PickerObject
		logger.Debug(fmt.Sprintf("input.Detail %v", v))
		// 预检查资源是否充足
		if v.Affinity == "" {
			v.Affinity = NONE
		}
		idcCitys, errx := getRealCitys(v.LocationSpec.City)
		if errx != nil {
			return pickers, errx
		}
		s := &SearchContext{
			BkCloudId:         param.BkCloudId,
			IntetionBkBizId:   param.ForbizId,
			RsType:            param.ResourceType,
			ApplyObjectDetail: &v,
			IdcCitys:          idcCitys,
		}
		if err = s.PickCheck(); err != nil {
			return pickers, err
		}
		// 挑选符合需求的资源
		picker, err = s.PickInstance()
		if err != nil {
			return pickers, fmt.Errorf("Picker for %s Failed,Error is %v", v.GroupMark, err)
		}
		// Debug Print Log 挑选实例分区的情况
		picker.DebugDistrubuteLog()
		// 更新挑选到的资源的状态为Preselected
		if update_err := picker.PreselectedSatisfiedInstance(); update_err != nil {
			return pickers, fmt.Errorf("update %s Picker Out Satisfied Instance Status In Selling Failed:%v", v.GroupMark,
				update_err.Error())
		}
		// 追加到挑选好的分组
		pickers = append(pickers, picker)
	}
	return pickers, nil
}

// RollBackAllInstanceUnused 将 Instance Status  Selling  ==> Not Selled : 2 --> 0
func RollBackAllInstanceUnused(ms []*PickerObject) {
	for _, m := range ms {
		if err := m.RollbackSatisfiedInstanceStatusUnused(); err != nil {
			logger.Error(fmt.Sprintf("Rollback Satisfied Instance Status NotSelled Failed,Error %s", err.Error()))
		}
	}
}

// Matcher TODO
func (o *SearchContext) Matcher() (fns []func(db *gorm.DB)) {
	switch {
	//  机型参数不存在、资源规格参数存在,匹配资源规格参数
	case len(o.DeviceClass) == 0 && o.Spec.NotEmpty():
		fns = append(fns, o.MatchSpec)
	// 机型参数存在、资源规格参数不存在,匹配机型
	case len(o.DeviceClass) > 0 && o.Spec.NotEmpty():
		fns = append(fns, o.MatchDeviceClass)
	// 机型参数存在、资源规格参数存在,先匹配机型,在匹配资源规格
	case len(o.DeviceClass) > 0 && o.Spec.NotEmpty():
		fns = append(fns, o.MatchSpec)
		fns = append(fns, o.MatchDeviceClass)
	}
	// 没有条件的时候也需要遍历一遍
	fns = append(fns, func(db *gorm.DB) {})
	return
}

func (o *SearchContext) pickBase(db *gorm.DB) (err error) {
	db.Where("gse_agent_status_code = ? ", bk.GSE_AGENT_OK)
	if o.BkCloudId <= 0 {
		db.Where(" bk_cloud_id = ? and status = ?  ", o.ApplyObjectDetail.BkCloudId, model.Unused)
	} else {
		db.Where(" bk_cloud_id = ? and status = ?  ", o.BkCloudId, model.Unused)
	}
	// 如果没有指定资源类型，表示只能选择无资源类型标签的资源
	// 没有资源类型标签的资源可以被所有其他类型使用
	if cmutil.IsEmpty(o.RsType) {
		db.Where("JSON_LENGTH(rs_types) <= 0")
	} else {
		db.Where("? or JSON_LENGTH(rs_types) <= 0 ", model.JSONQuery("rs_types").Contains([]string{o.RsType}))
	}
	// 如果没有指定专属业务，就表示只能选用公共的资源
	// 不能匹配打了业务标签的资源
	if o.IntetionBkBizId <= 0 {
		db.Where("JSON_LENGTH(dedicated_bizs) <= 0")
	} else {
		db.Where("? or JSON_LENGTH(dedicated_bizs) <= 0", model.JSONQuery("dedicated_bizs").Contains([]string{
			strconv.Itoa(o.IntetionBkBizId)}))
	}
	o.MatchLables(db)
	if err = o.MatchLocationSpec(db); err != nil {
		return err
	}
	o.MatchStorage(db)
	// 如果需要存在跨园区检查则需要判断是否存在网卡id,机架id等
	if o.Affinity == SAME_SUBZONE_CROSS_SWTICH {
		o.UseNetDeviceIsNotEmpty(db)
	}
	return nil
}

// PickCheck TODO
func (o *SearchContext) PickCheck() (err error) {
	var count int64
	db := model.DB.Self.Table(model.TbRpDetailName()).Select("count(*)")
	if err := o.pickBase(db); err != nil {
		return err
	}
	for _, fn := range o.Matcher() {
		fn(db)
		var cnt int64
		if err := db.Scan(&cnt).Error; err != nil {
			logger.Error("query pre check count failed %s", err.Error())
			return err
		}
		count += cnt
	}
	logger.Info("count is  %d", count)
	if int(count) < o.Count {
		return fmt.Errorf("[pre inspection]: total number of resources initially eligible:%d,number of interface requests:%d",
			count, o.Count)
	}
	return nil
}

// MatchLables TODO
func (o *SearchContext) MatchLables(db *gorm.DB) {
	if len(o.Labels) > 0 {
		for key, v := range o.Labels {
			db.Where(" ( json_contains(label,json_object(?,?) )", key, v)
		}
		return
	}
	db.Where(" JSON_TYPE(label) = 'NULL' OR JSON_LENGTH(label) <= 1 ")
}

// PickInstance TODO
func (o *SearchContext) PickInstance() (picker *PickerObject, err error) {
	picker = NewPicker(o.Count, o.GroupMark)
	for _, fn := range o.Matcher() {
		var items []model.TbRpDetail
		db := model.DB.Self.Table(model.TbRpDetailName())
		if err = o.pickBase(db); err != nil {
			return
		}
		fn(db)
		if err = db.Scan(&items).Error; err != nil {
			logger.Error("query failed %s", err.Error())
			return
		}
		// 过滤没有挂载点的磁盘匹配需求
		esspec := GetEmptyDiskSpec(o.StorageSpecs)
		if len(esspec) > 0 {
			ts := []model.TbRpDetail{}
			for _, ins := range items {
				if err := ins.UnmarshalDiskInfo(); err != nil {
					logger.Error("umarshal disk failed %s", err.Error())
				}
				logger.Info("%v", ins.Storages)
				noUseStorages := make(map[string]bk.DiskDetail)
				smp := GetDiskSpecMountPoints(o.StorageSpecs)
				for mp, v := range ins.Storages {
					if cmutil.ElementNotInArry(mp, smp) {
						noUseStorages[mp] = v
					}
				}
				logger.Info("nouse: %v", noUseStorages)
				if matchNoMountPointStorage(esspec, noUseStorages) {
					ts = append(ts, ins)
				}
			}
			if len(ts) <= 0 {
				return picker, fmt.Errorf("did not match the appropriate resources")
			}
			items = ts
		}
		o.PickInstanceBase(picker, items)
		logger.Info("picker now is %v", picker)
		if picker.PickerDone() {
			return picker, nil
		}
	}
	return nil, fmt.Errorf("all Instances Cannot Satisfy The Requested Parameters")
}

func matchNoMountPointStorage(spec []DiskSpec, sinc map[string]bk.DiskDetail) bool {
	mcount := 0
	for _, s := range spec {
		for mp, d := range sinc {
			if diskDetailMatch(d, s) {
				delete(sinc, mp)
				mcount += 1
				break
			}
		}
	}
	return mcount == len(spec)
}

func diskDetailMatch(d bk.DiskDetail, s DiskSpec) bool {
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
func (o *ApplyObjectDetail) PickInstanceBase(picker *PickerObject, items []model.TbRpDetail) {
	logger.Info("the anti-affinity is %s", o.Affinity)
	switch o.Affinity {
	case NONE:
		data := AnalysisResource(items, true)
		picker.PickeElements = data
		picker.PickerSameSubZone(false)
	case CROS_SUBZONE:
		data := AnalysisResource(items, false)
		picker.PickeElements = data
		picker.Picker(true)
	case SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH:
		data := AnalysisResource(items, false)
		picker.PickeElements = data
		picker.PickerSameSubZone(false)
	}
}

// MatchLocationSpec TODO
func (o *SearchContext) MatchLocationSpec(db *gorm.DB) (err error) {
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
	return
}

// MatchStorage TODO
func (o *SearchContext) MatchStorage(db *gorm.DB) {
	if len(o.StorageSpecs) <= 0 {
		return
	}
	for _, d := range o.StorageSpecs {
		if cmutil.IsNotEmpty(d.MountPoint) {
			mp := path.Clean(d.MountPoint)
			if cmutil.IsNotEmpty(d.DiskType) {
				db.Where(model.JSONQuery("storage_device").Equals(d.DiskType, mp, "disk_type"))
			}
			switch {
			case d.MaxSize > 0:
				db.Where(model.JSONQuery("storage_device").NumRange(d.MinSize, d.MaxSize, mp, "size"))
			case d.MaxSize <= 0 && d.MinSize > 0:
				db.Where(model.JSONQuery("storage_device").Gte(d.MinSize, mp, "size"))
			}
		}
	}
}

// MatchSpec TODO
// MatchSpec TODO
func (o *SearchContext) MatchSpec(db *gorm.DB) {
	db.Where(" ( cpu_num >= ?  and cpu_num <= ? ) and ( dram_cap >= ? and dram_cap <= ? ) ", o.Spec.Cpu.Min,
		o.Spec.Cpu.Max,
		o.Spec.Mem.Min, o.Spec.Mem.Max)
}

// MatchDeviceClass TODO
func (o *SearchContext) MatchDeviceClass(db *gorm.DB) {
	db.Where(" device_class in ? ", o.DeviceClass)
}

// UseNetDeviceIsNotEmpty TODO
func (o *SearchContext) UseNetDeviceIsNotEmpty(db *gorm.DB) {
	db.Where("(net_device_id  is not null or  net_device_id != '') and (rack_id is not null or rack_id != '')")
}
