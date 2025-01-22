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
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ParamCheck TODO
func (param *RequestInputParam) ParamCheck() (err error) {
	for _, a := range param.Details {
		for _, d := range a.StorageSpecs {
			if d.MaxSize > 0 && d.MinSize > d.MaxSize {
				return fmt.Errorf("min %d great thane min %d", d.MinSize, d.MaxSize)
			}
		}
		if !a.Spec.Cpu.Iegal() {
			return fmt.Errorf("cpu参数不合法: min:%d,max:%d", a.Spec.Cpu.Min, a.Spec.Cpu.Max)
		}
		if !a.Spec.Mem.Iegal() {
			return fmt.Errorf("mem参数不合法: min:%d,max:%d", a.Spec.Mem.Min, a.Spec.Mem.Max)
		}
		// 如果只是申请一个机器，则没有亲和性的必要
		if a.Count <= 1 {
			continue
		}
		switch a.Affinity {
		case SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH:
			if a.LocationSpec.IsEmpty() {
				return fmt.Errorf("you need choose a city !!! ")
			}
		case CROS_SUBZONE:
			if a.LocationSpec.IsEmpty() {
				return fmt.Errorf("you need choose a city !!! ")
			}
			if !a.LocationSpec.IsExclude() && (len(a.LocationSpec.SubZoneIds) > 0 && len(a.LocationSpec.SubZoneIds) < 2) {
				return fmt.Errorf("because need cros subzone,you special subzones need more than 2 subzones")
			}
		case NONE:
			return nil
		}
	}
	return nil
}

// ActionInfo TODO
type ActionInfo struct {
	TaskId   string `json:"task_id"`
	BillId   string `json:"bill_id"`
	BillType string `json:"bill_type"`
	Operator string `json:"operator"`
}

// RequestInputParam 请求接口参数
type RequestInputParam struct {
	ResourceType         string         `json:"resource_type"` // 申请的资源用作的用途 Redis|MySQL|Proxy
	DryRun               bool           `json:"dry_run"`
	ForbizId             int            `json:"for_biz_id"`
	Details              []ObjectDetail `json:"details" binding:"required,gt=0,dive"`
	GroupsInSameLocation bool           `json:"groups_in_same_location"`
	ActionInfo
}

// GetAllAffinitys 获取这批请求的所有亲和性的参数
func (param RequestInputParam) GetAllAffinitys() (affinitys []string) {
	for _, d := range param.Details {
		if !lo.Contains(affinitys, d.Affinity) {
			affinitys = append(affinitys, d.Affinity)
		}
	}
	return affinitys
}

// BuildMessage build apply message
func (param RequestInputParam) BuildMessage() (msg string) {
	var count int
	groupMap := make(map[string]int)
	groupCountMap := make(map[string]int)
	for _, d := range param.Details {
		groupMap[d.Affinity]++
		groupCountMap[d.Affinity] += d.Count
		count += d.Count
	}
	msg = fmt.Sprintf("此次申请分%d组申请%d个机器\n", len(param.Details), count)
	for affinity, count := range groupMap {
		msg += fmt.Sprintf("按照亲和性%s申请的资源分组%d,总共包含机器数量%d\n", affinity, count, groupCountMap[affinity])
	}
	return msg
}

// SpecialSubZoneIds get special subzone ids
func (param RequestInputParam) SpecialSubZoneIds() (specialZones []string, isExclude bool) {
	d := param.Details[0]
	return d.LocationSpec.SubZoneIds, d.LocationSpec.IsExclude()
}

// SortDetails 优先去匹配有明确需求的参数
func (param RequestInputParam) SortDetails() ([]ObjectDetail, error) {
	if len(param.Details) == 1 {
		return param.Details, nil
	}
	var dlts []ObjectDetail
	pq := NewPriorityQueue()
	for idx, dtlp := range param.Details {
		item := Item{
			Key:      strconv.Itoa(idx),
			Value:    dtlp,
			Priority: 0,
		}
		if len(dtlp.StorageSpecs) > 0 {
			// 多磁盘需求前置
			item.Priority += int64(len(dtlp.StorageSpecs))
		}
		if !dtlp.LocationSpec.IsEmpty() {
			item.Priority++
			if !dtlp.LocationSpec.SubZoneIsEmpty() {
				item.Priority++
			}
		}
		if len(dtlp.DeviceClass) > 0 {
			item.Priority++
		}
		if err := pq.Push(&item); err != nil {
			return nil, err
		}
	}
	for pq.Len() > 0 {
		item, err := pq.Pop()
		if err != nil {
			return nil, err
		}
		dlts = append(dlts, item.Value.(ObjectDetail))
	}
	return dlts, nil
}

// GetOperationInfo TODO
func (param RequestInputParam) GetOperationInfo(requestId, mode string,
	data []model.BatchGetTbDetailResult) model.TbRpOperationInfo {
	var count int
	var bkHostIds []int
	var ipList []string
	for _, v := range param.Details {
		count += v.Count
	}
	for _, group := range data {
		bkHostIds = append(bkHostIds, lo.Map(group.Data, func(d model.TbRpDetail, _ int) int {
			return d.BkHostID
		})...)
		ipList = append(ipList, lo.Map(group.Data, func(d model.TbRpDetail, _ int) string {
			return d.IP
		})...)
	}
	var desc string
	bkHostIdsBytes, err := json.Marshal(bkHostIds)
	if err != nil {
		desc += "failed to serialize bkhost ids"
		logger.Error("json marshal failed  %s", err.Error())
	}
	ipListBytes, err := json.Marshal(ipList)
	if err != nil {
		desc += "failed to serialize ipList"
		logger.Error("json marshal failed  %s", err.Error())
	}
	return model.TbRpOperationInfo{
		RequestID:     requestId,
		TotalCount:    count,
		OperationType: model.Consumed,
		BkHostIds:     bkHostIdsBytes,
		IpList:        ipListBytes,
		BillId:        param.BillId,
		BillType:      param.BillType,
		TaskId:        param.TaskId,
		Operator:      param.Operator,
		Status:        mode,
		CreateTime:    time.Now(),
		UpdateTime:    time.Now(),
		Description:   desc,
	}
}

// LockKey get lock key
func (param RequestInputParam) LockKey() string {
	if cmutil.IsEmpty(param.ResourceType) {
		return fmt.Sprintf("dbrms:lock:bizid.%d", param.ForbizId)
	}
	return fmt.Sprintf("dbrms:lock:%s:bizid.%d", param.ResourceType, param.ForbizId)
}

const (
	// SAME_SUBZONE_CROSS_SWTICH 同城同园区跨交换机跨机架
	SAME_SUBZONE_CROSS_SWTICH = "SAME_SUBZONE_CROSS_SWTICH"
	// SAME_SUBZONE 同城同园区
	SAME_SUBZONE = "SAME_SUBZONE"
	// CROS_SUBZONE 同城跨园区
	CROS_SUBZONE = "CROS_SUBZONE"
	// MAX_EACH_ZONE_EQUAL 尽量每个zone分配数量相等
	MAX_EACH_ZONE_EQUAL = "MAX_EACH_ZONE_EQUAL"
	// CROSS_RACK 跨机架
	CROSS_RACK = "CROSS_RACK"
	// NONE 无亲和性
	NONE = "NONE"
)

// ObjectDetail 资源申请对象详情
// 反亲和性 目前只有一种选项,当campus是空的时候，则此值生效
// SAME_SUBZONE_CROSS_SWTICH: 同城同subzone跨交换机跨机架、
// SAME_SUBZONE: 同城同subzone
// CROS_SUBZONE：同城跨subzone
// NONE: 无需亲和性处理
type ObjectDetail struct {
	BkCloudId int      `json:"bk_cloud_id"`
	Hosts     Hosts    `json:"hosts"`                          // 主机id
	GroupMark string   `json:"group_mark" binding:"required" ` // 资源组标记
	Labels    []string `json:"labels"`                         // 标签
	// 通过机型规格 或者 资源规格描述来匹配资源
	// 这两个条件是 || 关系
	DeviceClass  []string          `json:"device_class"` // 机器类型 "IT5.8XLARGE128" "SA3.2XLARGE32"
	Spec         meta.Spec         `json:"spec"`         // 规格描述
	StorageSpecs []meta.DiskSpec   `json:"storage_spec"`
	LocationSpec meta.LocationSpec `json:"location_spec"` // 地域区间

	Affinity string `json:"affinity"`
	// Windows,Linux
	OsType        string   `json:"os_type"`
	OsNames       []string `json:"os_names"`
	ExcludeOsName bool     `json:"exclude_os_name"`
	Count         int      `json:"count" binding:"required,min=1"` // 申请数量
}

// Hosts bk hosts
type Hosts []Host

// GetBkHostIds get bk host ids
func (a Hosts) GetBkHostIds() []int {
	var bkHostIds []int
	for _, v := range a {
		bkHostIds = append(bkHostIds, v.BkHostId)
	}
	return bkHostIds
}

// Host bk host
type Host struct {
	BkHostId int    `json:"bk_host_id"`
	IP       string `json:"ip"`
}

// GetDiskMatchInfo get request disk message
func (a *ObjectDetail) GetDiskMatchInfo() (message string) {
	if len(a.StorageSpecs) > 0 {
		for _, d := range a.StorageSpecs {
			if cmutil.IsNotEmpty(d.MountPoint) {
				message += fmt.Sprintf("disk: mount point: %s", d.MountPoint)
			}
			if !cmutil.IsNotEmpty(d.DiskType) {
				message += " disk type: " + d.DiskType
			}
			switch {
			case d.MaxSize > 0 && d.MinSize > 0:
				message += fmt.Sprintf(" size: %d ~  %d G ", d.MinSize, d.MaxSize)
			case d.MaxSize > 0 && d.MaxSize <= 0:
				message += fmt.Sprintf(" size <= %d G ", d.MaxSize)
			case d.MaxSize <= 0 && d.MinSize > 0:
				message += fmt.Sprintf(" size >= %d G ", d.MinSize)
			}
		}
		message += "\n\r"
	}
	return
}

// GetMessage return apply failed message
func (a *ObjectDetail) GetMessage() (message string) {
	message += fmt.Sprintf("group: %s\n\r", a.GroupMark)
	if len(a.DeviceClass) > 0 {
		message += fmt.Sprintf("device_class: %v\n\r", a.DeviceClass)
	}
	if a.Spec.NotEmpty() {
		if a.Spec.Cpu.IsNotEmpty() {
			message += fmt.Sprintf("cpu: %d ~ %d 核\n\r", a.Spec.Cpu.Min, a.Spec.Cpu.Max)
		}
		if a.Spec.Mem.IsNotEmpty() {
			message += fmt.Sprintf("mem: %d ~ %d M\n\r", a.Spec.Mem.Min, a.Spec.Mem.Max)
		}
	}
	message += a.GetDiskMatchInfo()
	if !a.LocationSpec.IsEmpty() {
		message += fmt.Sprintf("city: %s \n\r", a.LocationSpec.City)
		if len(a.LocationSpec.SubZoneIds) > 0 {
			if a.LocationSpec.IsExclude() {
				message += fmt.Sprintf("subzoneId must not exist in the  %v", a.LocationSpec.SubZoneIds)
			} else {
				message += fmt.Sprintf("subzoneId  must exist in the %v", a.LocationSpec.SubZoneIds)
			}
		}
	}
	switch a.Affinity {
	case NONE:
		message += "资源亲和性： NONE\n\r"
	case CROS_SUBZONE:
		message += "资源亲和性： 同城跨园区\n\r"
	case SAME_SUBZONE:
		message += "资源亲和性： 同城同园区\n\r"
	case SAME_SUBZONE_CROSS_SWTICH:
		message += "资源亲和性： 同城同园区 跨交换机跨机架\n\r"
	}
	message += fmt.Sprintf("申请总数: %d \n\r", a.Count)
	return message
}
