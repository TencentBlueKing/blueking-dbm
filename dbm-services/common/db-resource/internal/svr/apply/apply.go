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
	"time"

	"github.com/patrickmn/go-cache"
	"github.com/samber/lo"
	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"
)

// SearchContext describe search context
type SearchContext struct {
	*ObjectDetail
	RsType            string
	IntentionBkBizId  int
	IdcCitys          []string
	SpecialSubZoneIds []string
	SpecialHostIds    []int
}

// applyGroupsInSameLocation apply groups in same location
func applyGroupsInSameLocation(param RequestInputParam) (pickers []*PickerObject, err error) {
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
		logger.Error("get logic cites failed %s", err.Error())
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
		msg := "没有符合条件的资源"
		// 未进入 PickCheck,没有逐步筛选的漏斗数据
		return pickers, NewResourceInsufficientError(ApplyFailureEvidence{
			Stage:        FailStagePickCheck,
			RequestCount: v.Count,
			Affinity:     v.Affinity,
			Note:         "多分组要求落在同一园区,合并各分组的园区优先级后候选园区为空,未执行按条件逐步筛选",
		}, errno.ErrResourceinsufficient.Add(msg), msg)
	}
	for _, subzoneId := range subzoneIds {
		pickers = []*PickerObject{}
		for _, v := range resourceReqList {
			s := &SearchContext{
				IntentionBkBizId:  param.ForbizId,
				RsType:            model.NormalizeResourceType(param.ResourceType),
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
			picker.DebugDistributeLog()
			// 更新挑选到的资源的状态为Preselected
			if updateErr := picker.PreselectedSatisfiedInstance(); updateErr != nil {
				err = newPreselectFailedError(&v, picker, updateErr)
				logger.Error("挑选资源失败:%v", err)
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
			IntentionBkBizId: param.ForbizId,
			RsType:           model.NormalizeResourceType(param.ResourceType),
			ObjectDetail:     &v,
			IdcCitys:         idcCitys,
			SpecialHostIds:   v.Hosts.GetBkHostIds(),
		}
		var items []model.TbRpDetail
		db := model.DB.Self.Table(model.TbRpDetailName())
		s.pickBase(db)
		if err = db.Scan(&items).Error; err != nil {
			logger.Error("query failed %s", err.Error())
			return nil, errno.ErrDBQuery.AddErr(err)
		}
		campusSummary := make(map[string]*SubZoneSummary)
		for _, item := range items {
			if _, ok := campusSummary[item.SubZoneID]; !ok {
				campusSummary[item.SubZoneID] = &SubZoneSummary{
					Count:             1,
					RackIdList:        []string{item.RackID},
					LinkNetdeviceList: strings.Split(item.NetDeviceID, ","),
					RequestCount:      v.Count,
				}
			} else {
				campusSummary[item.SubZoneID].Count++
				campusSummary[item.SubZoneID].RackIdList = append(campusSummary[item.SubZoneID].RackIdList, item.RackID)

				campusSummary[item.SubZoneID].LinkNetdeviceList = append(campusSummary[item.SubZoneID].LinkNetdeviceList,
					strings.Split(item.NetDeviceID, ",")...)
			}
		}
		groupcampusNice[v.GroupMark] = campusSummary
	}
	return groupcampusNice, nil
}

func sortgroupcampusNice(gpms map[string]map[string]*SubZoneSummary) []string {
	subzones := []string{}
	gcnsMap := make(map[string]*CampusNice)
	var cns []CampusNice
	for _, campusSummary := range gpms {
		for campus := range campusSummary {
			equipmentIdList := lo.Uniq(campusSummary[campus].RackIdList)
			linkNetdeviceList := lo.Uniq(campusSummary[campus].LinkNetdeviceList)
			count := campusSummary[campus].Count
			requestCount := campusSummary[campus].RequestCount
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
	RackIdList        []string // 存在的设备Id
	LinkNetdeviceList []string // 存在的网卡Id
}

func getLogicIdcCitys(v ObjectDetail) (idcCitys []string, err error) {
	if config.AppConfig.RunMode == "dev" {
		idcCitys = []string{}
	} else if cmutil.ElementNotInArry(v.Affinity, []string{CROSS_RACK, NONE, CROSS_SUBZONE_STRONG, CROSS_SUBZONE_WEAK}) ||
		lo.IsNotEmpty(v.LocationSpec.City) ||
		len(v.Hosts) > 0 {
		idcCitys, err = dbmapi.GetIdcCityByLogicCity(v.LocationSpec.City)
		if err != nil {
			logger.Error("request real cites by logic city %s from bk-dbm api failed:%v", v.LocationSpec.City, err)
			return []string{}, err
		}
	}
	return idcCitys, nil
}

// CycleApply 循环匹配
func CycleApply(param RequestInputParam) (pickers []*PickerObject, err error) {
	param.NormalizeAffinities()
	// 多个请求参数分组在同一个地方
	affinities := lo.Uniq(param.GetAllAffinities())
	if param.GroupsInSameLocation && len(param.Details) > 1 && len(affinities) == 1 &&
		slices.Contains([]string{SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH}, affinities[0]) {
		logger.Info("apply all groups in same location")
		return applyGroupsInSameLocation(param)
	}
	// 使用原有的顺序分配策略
	return cycleApplySequential(param)
}

// cycleApplySequential 原有的顺序分配策略
func cycleApplySequential(param RequestInputParam) (pickers []*PickerObject, err error) {
	resourceReqList, err := param.SortDetails()
	if err != nil {
		logger.Error("对请求参数排序失败%v", err)
		return nil, err
	}
	cityMapCache := cache.New(2*time.Minute, 30*time.Second)
	defer cityMapCache.Flush()
	for _, v := range resourceReqList {
		var picker *PickerObject
		logger.Debug(fmt.Sprintf("input.Detail %v", v))
		v.Affinity = NormalizeAffinity(v.Affinity)
		idcCites := []string{}
		if lo.IsNotEmpty(&v.LocationSpec.City) {
			idcCites, err = getLogicIdcCitys(v)
			if err != nil {
				logger.Error("get logic cites failed %s", err.Error())
				return pickers, err
			}
		}
		s := &SearchContext{
			IntentionBkBizId: param.ForbizId,
			RsType:           model.NormalizeResourceType(param.ResourceType),
			ObjectDetail:     &v,
			IdcCitys:         idcCites,
			SpecialHostIds:   v.Hosts.GetBkHostIds(),
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
		picker.DebugDistributeLog()
		// 更新挑选到的资源的状态为Preselected
		if updateErr := picker.PreselectedSatisfiedInstance(); updateErr != nil {
			return pickers, newPreselectFailedError(&v, picker, updateErr)
		}
		// 追加到挑选好的分组
		pickers = append(pickers, picker)
	}
	return pickers, nil
}

// RollBackAllInstanceUnused reserve all instance unused
func RollBackAllInstanceUnused(ms []*PickerObject) {
	for _, m := range ms {
		logger.Info("Rollback Satisfied Instance Status to Unused,HostIds %v", m.SatisfiedHostIds)
		if err := m.RollbackUnusedInstance(); err != nil {
			logger.Error(fmt.Sprintf("Rollback Satisfied Instance Status to Unused Failed,Error %s", err.Error()))
		}
	}
}

// matchStep 一个匹配条件及其叠加顺序
type matchStep struct {
	name string
	fn   func(db *gorm.DB)
	desc string
}

// matchSteps 返回按顺序叠加的匹配条件。
// pickBase 与 CollectMatchFunnel 共用这份定义，保证漏斗观测到的顺序就是真实申请的顺序。
func (o *SearchContext) matchSteps() []matchStep {
	steps := []matchStep{
		{
			name: "base",
			fn: func(db *gorm.DB) {
				db.Where("bk_cloud_id = ? and status = ? and gse_agent_status_code = ? ",
					o.BkCloudId, model.Unused, bk.GseAlive)
			},
			desc: fmt.Sprintf("云区域%d,gse_agent 状态正常的未使用资源", o.BkCloudId),
		},
		{name: "biz", fn: o.MatchIntentionBkBiz, desc: "叠加专用业务/公共业务后"},
		{name: "rsType", fn: o.MatchRsType, desc: "叠加资源类型后"},
		{name: "osType", fn: o.MatchOsType, desc: "叠加操作系统类型后"},
		{name: "osName", fn: o.MatchOsName, desc: "叠加操作系统名称后"},
		{name: "labels", fn: o.MatchLabels, desc: "叠加标签后"},
		{name: "location", fn: o.MatchLocationSpec, desc: "叠加地域信息后"},
		{name: "storage", fn: o.MatchStorage, desc: "叠加磁盘条件(仅带挂载点)后"},
		{name: "spec", fn: o.MatchSpec, desc: "叠加规格[cpu/mem或机型]后"},
	}
	// 如果需要存在跨园区检查则需要判断是否存在网卡id,机架id等
	switch o.Affinity {
	case SAME_SUBZONE_CROSS_SWTICH:
		steps = append(steps, matchStep{
			name: "netDevice",
			fn:   o.UseNetDeviceIsNotEmpty,
			desc: "亲和性为同园区跨交换机,叠加网卡id非空后",
		})
	case CROSS_RACK, CROSS_SUBZONE_STRONG, CROSS_SUBZONE_WEAK:
		steps = append(steps, matchStep{
			name: "rackId",
			fn:   o.RackIdIsNotEmpty,
			desc: "亲和性为跨机架或跨园区(强/弱),叠加机架id非空后",
		})
	}
	return steps
}

func (o *SearchContext) pickBase(db *gorm.DB) {
	// 如果指定了特殊资源，就只查询这些资源
	if len(o.SpecialHostIds) > 0 {
		db.Where("bk_host_id in (?) and status = ? and gse_agent_status_code = ? ", o.SpecialHostIds, model.Unused,
			bk.GseAlive)
		return
	}
	for _, step := range o.matchSteps() {
		step.fn(db)
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
	if err = db.Scan(&count).Error; err != nil {
		logger.Error("query pre check count failed %s", err.Error())
		return errno.ErrDBQuery.AddErr(err)
	}

	if int(count) < o.Count {
		funnel, ferr := o.CollectMatchFunnel()
		if ferr != nil {
			logger.Error("collect match funnel failed %s", ferr.Error())
		}
		msg := fmt.Sprintf("申请需求:\n%s 资源池符合条件的资源总数%d 小于申请的数量", o.GetMessage(), count)
		if detail := FormatFunnel(funnel); detail != "" {
			msg += "\n\n" + detail
		}
		logger.Error("%s", msg)
		return NewResourceInsufficientError(ApplyFailureEvidence{
			Stage:        FailStagePickCheck,
			GroupMark:    o.GroupMark,
			Affinity:     o.Affinity,
			RequestCount: o.Count,
			Funnel:       funnel,
			Note:         funnelStorageNote,
		}, nil, msg)
	}
	return nil
}

// funnelStorageNote 漏斗的观测边界：SQL 阶段只覆盖带挂载点的磁盘条件
const funnelStorageNote = "漏斗的 storage 步骤只覆盖带 mount_point 的 SQL 磁盘条件;" +
	"未指定 mount_point 的磁盘需求在后续内存阶段过滤,因此 SQL 剩余台数可能大于实际可进入分配的台数"

// CollectMatchFunnel 按 pickBase 的同一顺序逐步叠加匹配条件,记录每步剩余台数。
// 这里只产出观测数字:count 的下降依赖叠加顺序,不据此推断根因。
func (o *SearchContext) CollectMatchFunnel() (funnel []MatchStageCount, err error) {
	db := model.DB.Self.Table(model.TbRpDetailName()).Select("count(*)")
	// 与 pickBase 共用同一份步骤定义，逐步叠加并记录每步剩余台数
	for _, step := range o.matchSteps() {
		step.fn(db)
		var count int64
		if err = db.Scan(&count).Error; err != nil {
			logger.Error("collect funnel stage %s failed %s", step.name, err.Error())
			return funnel, err
		}
		funnel = append(funnel, MatchStageCount{
			Name:        step.name,
			Count:       count,
			Requested:   o.Count,
			Description: step.desc,
		})
	}
	return funnel, nil
}

// PickCheckSpecialBkhostIds host Ids 根据bk host ids取资源
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
		for hostId, ip := range hostIpMap {
			if !lo.Contains(rs, hostId) {
				emptyIps = append(emptyIps, ip)
			}
		}
		msg := fmt.Sprintf("指定ip申请资源,部分资源不存在:%v", emptyIps)
		// 指定主机不经过 pickBase 的逐步过滤,没有漏斗可采集
		return NewResourceInsufficientError(ApplyFailureEvidence{
			Stage:        FailStagePickCheck,
			GroupMark:    o.GroupMark,
			Affinity:     o.Affinity,
			RequestCount: o.Count,
			MissingIps:   emptyIps,
			Note:         "指定 bk_host_id 申请,未经过按条件逐步筛选,无漏斗数据",
		}, nil, msg)
	}
	return nil
}

// filterEmptyMountPointStorage 过滤没有挂载点的磁盘匹配需求
func (o *SearchContext) filterEmptyMountPointStorage(items []model.TbRpDetail,
	diskSpecs []meta.DiskSpec) (ts []model.TbRpDetail, err error) {
	for _, ins := range items {
		if err = ins.UnmarshalDiskInfo(); err != nil {
			logger.Error("%s unmarshal disk failed %s", ins.IP, err.Error())
			return nil, err
		}
		logger.Info("%v", ins.Storages)
		noUseStorages := make(map[string]bk.DiskDetail)
		smp := meta.GetDiskSpecMountPoints(o.StorageSpecs)
		for mp, v := range ins.Storages {
			if !slices.Contains(smp, mp) {
				noUseStorages[mp] = v
			}
		}
		logger.Info("no-use: %v", noUseStorages)
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
		beforeFilter := len(items)
		items, err = o.filterEmptyMountPointStorage(items, diskSpecs)
		if err != nil {
			logger.Error("filter empty mount point storage failed %s", err.Error())
			return picker, NewResourceInsufficientError(ApplyFailureEvidence{
				Stage:          FailStageEmptyMountDisk,
				GroupMark:      o.GroupMark,
				Affinity:       o.Affinity,
				RequestCount:   o.Count,
				CandidateCount: beforeFilter,
				PickedCount:    len(items),
				Note:           "SQL 阶段候选台数为 candidate_count,按未占用挂载点匹配磁盘后剩余 picked_count",
			}, err, err.Error())
		}
	}

	if err = o.PickInstanceBase(picker, items); err != nil {
		return nil, err
	}

	if picker.PickerDone() {
		return picker, nil
	}

	msg := fmt.Sprintf("Picker for %s, 所有资源无法满足 %s的参数需求", o.GroupMark, o.GetMessage())
	return nil, NewResourceInsufficientError(ApplyFailureEvidence{
		Stage:          FailStageAffinity,
		GroupMark:      o.GroupMark,
		Affinity:       o.Affinity,
		RequestCount:   o.Count,
		CandidateCount: len(items),
		PickedCount:    len(picker.SatisfiedHostIds),
		ProcessLogs:    picker.ProcessLogs,
		Distribution:   BuildAffinitySnapshot(o.Affinity, o.Count, items),
		Note:           "process_logs 为分配过程日志,不是结论",
	}, errno.ErrResourceinsufficient.Add(msg), msg)
}

// PickInstanceBase pick instance base
func (o *SearchContext) PickInstanceBase(picker *PickerObject, items []model.TbRpDetail) (err error) {
	logger.Info("the anti-affinity is %s", o.Affinity)
	picker.Affinity = o.Affinity
	if len(o.SpecialHostIds) > 0 {
		for _, v := range items {
			if slices.Contains(o.SpecialHostIds, v.BkHostID) {
				picker.SatisfiedHostIds = append(picker.SatisfiedHostIds, v.BkHostID)
			}
		}
		picker.Count = len(o.SpecialHostIds)
		return nil
	}
	switch o.Affinity {
	case NONE:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, true)
		picker.PickerRandom()
	case CROS_SUBZONE:
		// 初始化容忍度配置
		picker.InitToleranceConfig(o.Tolerance, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerCrossSubzone(true, false)
	case MAX_EACH_ZONE_EQUAL:
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		if err != nil {
			return err
		}
		// 先跨园区选一遍
		picker.PickerCrossSubzone(true, false)
		if picker.PickerDone() {
			return
		}
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		if err != nil {
			return err
		}
		logger.Info("picker priority elements %d", len(picker.PriorityElements))
		// 在循环园区 跨机架选一遍
		picker.PickerCrossSubzone(false, true)
		if picker.PickerDone() {
			return
		}
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		if err != nil {
			return err
		}
		logger.Info("picker priority elements %d", len(picker.PriorityElements))
		// 在循环园区 选一遍
		picker.PickerCrossSubzone(false, false)
	case SAME_SUBZONE:
		// 初始化机架级容忍度配置
		picker.InitRackToleranceConfig(o.Tolerance, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(false)
	case SAME_SUBZONE_CROSS_SWTICH:
		// 初始化机架级容忍度配置
		picker.InitRackToleranceConfig(o.Tolerance, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerSameSubZone(true)
	case CROSS_RACK:
		picker.InitRackToleranceConfig(o.Tolerance, o.CurrentHosts, o.Count)
		picker.InitRackForCrossRack(o.CurrentHosts)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, true)
		picker.PickerSameSubZone(true)
	case MAJORITY_ELECTION_DISTRI:
		// 初始化园区级容忍度配置（限制每个园区最多 ceil(n/2) 台机器）
		logger.Info(" ================ InitToleranceConfig, tolerance: %f, currentHosts: %v, count: %d",
			o.Tolerance, o.CurrentHosts, o.Count)
		picker.InitToleranceConfig(o.Tolerance, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		picker.PickerMajorityElectionCrossSubzone()
	case CROSS_SUBZONE_STRONG:
		// 跨园区(强)：至少3个园区，园区容忍度1/3，同一园区至少2机架，机架容忍度1/2
		logger.Info(" ================ InitDualToleranceConfig, subzoneTolerance: %f, rackTolerance: %f, "+
			"currentHosts: %v, count: %d", 1.0/3.0, 0.5, o.CurrentHosts, o.Count)
		picker.InitDualToleranceConfig(1.0/3.0, 0.5, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		if err != nil {
			return err
		}
		picker.PickerCrossSubzoneWithRackTolerance()
	case CROSS_SUBZONE_WEAK:
		// 跨园区(弱)：至少2个园区，园区容忍度1/2，同一园区至少2机架，机架容忍度1/2
		logger.Info(" ================ InitDualToleranceConfig, subzoneTolerance: %f, rackTolerance: %f, "+
			"currentHosts: %v, count: %d", 0.5, 0.5, o.CurrentHosts, o.Count)
		picker.InitDualToleranceConfig(0.5, 0.5, o.CurrentHosts, o.Count)
		picker.PriorityElements, picker.SubZonePrioritySumMap, err = o.AnalysisResourcePriority(items, false)
		if err != nil {
			return err
		}
		picker.PickerCrossSubzoneWithRackTolerance()
	}
	return
}

// MatchIntentionBkBiz match intention biz
func (o *SearchContext) MatchIntentionBkBiz(db *gorm.DB) {
	// 如果没有指定专属业务，就表示只能选用公共的资源
	// 不能匹配打了业务标签的资源
	if o.IntentionBkBizId <= 0 {
		db.Where("dedicated_biz = 0")
	} else {
		if len(o.Labels) > 0 {
			db.Where("dedicated_biz  = ?", o.IntentionBkBizId)
		} else {
			db.Where("dedicated_biz in (?)", []int{0, o.IntentionBkBizId})
		}
	}
}

// MatchRsType pick rs type
func (o *SearchContext) MatchRsType(db *gorm.DB) {
	// 如果没有指定资源类型，表示只能选择无资源类型标签的资源
	// 没有资源类型标签的资源可以被所有其他类型使用
	switch {
	case lo.IsEmpty(o.RsType):
		db.Where("rs_type = ? ", model.RESOURCE_TYPE_PUBLIC)
	// 临时代码，后续需要删除 redis/mongodb 不匹配公共资源池的机器
	// ----------------------------
	case o.RsType == model.RESOURCE_TYPE_REDIS:
		db.Where("rs_type = ? ", model.RESOURCE_TYPE_REDIS)
	case o.RsType == model.RESOURCE_TYPE_MONGODB:
		db.Where("rs_type = ? ", model.RESOURCE_TYPE_MONGODB)
	// ------ 临时代码结束 ------
	default:
		db.Where("rs_type in (?)", []string{model.RESOURCE_TYPE_PUBLIC, o.RsType})
	}
}

// MatchOsType match os type
func (o *SearchContext) MatchOsType(db *gorm.DB) {
	// os type: Windows, Linux
	osType := o.ObjectDetail.OsType
	if cmutil.IsEmpty(o.ObjectDetail.OsType) {
		osType = model.LinuxOs
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
	if len(o.LocationSpec.ExcludeSubZoneIds) > 0 {
		db.Where("sub_zone_id not in (?)", o.LocationSpec.ExcludeSubZoneIds)
	}
	if len(o.LocationSpec.ExcludeRackIds) > 0 {
		db.Where("rack_id not in (?)", o.LocationSpec.ExcludeRackIds)
	}
	if len(o.LocationSpec.ExcludeNetDeviceIds) > 0 {
		db.Where("net_device_id not in (?)", o.LocationSpec.ExcludeNetDeviceIds)
	}
}

// MatchStorage  match storage parameters
func (o *SearchContext) MatchStorage(db *gorm.DB) {
	if len(o.StorageSpecs) == 0 {
		return
	}
	allSpecMinIsZero := false
	AndQ := []interface{}{}
	for _, d := range o.StorageSpecs {
		if lo.IsEmpty(d.MountPoint) {
			continue
		}
		mp := path.Clean(d.MountPoint)
		if isWindowsPath(mp) {
			mp = strings.ReplaceAll(mp, `\`, ``)
		}
		if cmutil.IsNotEmpty(d.DiskType) {
			AndQ = append(AndQ, model.JSONQuery("storage_device").Equals(d.DiskType, mp, "disk_type"))
			// db.Where(model.JSONQuery("storage_device").Equals(d.DiskType, mp, "disk_type"))
		}
		logger.Info("storage spec is %v", d)
		switch {
		case d.MaxSize > 0:
			AndQ = append(AndQ, model.JSONQuery("storage_device").NumRange(d.MinSize, d.MaxSize, mp, "size"))
			// db.Where(model.JSONQuery("storage_device").NumRange(d.MinSize, d.MaxSize, mp, "size"))
		case d.MaxSize <= 0 && d.MinSize > 0:
			AndQ = append(AndQ, model.JSONQuery("storage_device").Gte(d.MinSize, mp, "size"))
		}
		if d.MinSize == 0 {
			allSpecMinIsZero = true
		}
	}
	// 构建条件占位符
	var condStr string
	if len(AndQ) > 0 {
		conds := make([]string, len(AndQ))
		for i := range conds {
			conds[i] = "?"
		}
		condStr = strings.Join(conds, " AND ")

		// 如果所有规格的最小值都为0，添加空设备的OR条件
		if allSpecMinIsZero {
			condStr = "(" + condStr + ") OR (storage_device IS NULL OR JSON_LENGTH(storage_device) = 0)"
		}
		db.Where(condStr, AndQ...)
	} else if allSpecMinIsZero {
		// 没有其他条件时，只匹配空设备
		db.Where("storage_device IS NULL OR JSON_LENGTH(storage_device) = 0")
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

// UseNetDeviceIsNotEmpty filter net device id not empty
func (o *SearchContext) UseNetDeviceIsNotEmpty(db *gorm.DB) {
	db.Where("(net_device_id  is not null and net_device_id != '') and (rack_id is not null and rack_id != '')")
}

// RackIdIsNotEmpty filter rack-id is not empty
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
	if strings.TrimSpace(d.DiskType) != strings.TrimSpace(s.DiskType) && lo.IsNotEmpty(s.DiskType) {
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
