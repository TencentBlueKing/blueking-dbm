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
	"path"
	"time"

	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ParamCheck TODO
func (param *ApplyRequestInputParam) ParamCheck() (err error) {
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
			if a.LocationSpec.IncludeOrExclude && len(a.LocationSpec.SubZoneIds) < 2 {
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

// ApplyRequestInputParam 请求接口参数
type ApplyRequestInputParam struct {
	ResourceType string              `json:"resource_type"` // 申请的资源用作的用途 Redis|MySQL|Proxy
	DryRun       bool                `json:"dry_run"`
	BkCloudId    int                 `json:"bk_cloud_id"`
	ForbizId     int                 `json:"for_biz_id"`
	Details      []ApplyObjectDetail `json:"details" binding:"required,gt=0,dive"`
	ActionInfo
}

// GetOperationInfo TODO
func (c ApplyRequestInputParam) GetOperationInfo(requestId, mode string,
	data []model.BatchGetTbDetailResult) model.TbRpOperationInfo {
	var count int
	var bkHostIds []int
	var ipList []string
	for _, v := range c.Details {
		count += v.Count
	}
	for _, group := range data {
		for _, host := range group.Data {
			bkHostIds = append(bkHostIds, host.BkHostID)
			ipList = append(ipList, host.IP)
		}
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
		BillId:        c.BillId,
		BillType:      c.BillType,
		TaskId:        c.TaskId,
		Operator:      c.Operator,
		Status:        mode,
		CreateTime:    time.Now(),
		UpdateTime:    time.Now(),
		Desc:          desc,
	}
}

// LockKey TODO
func (c ApplyRequestInputParam) LockKey() string {
	if cmutil.IsEmpty(c.ResourceType) {
		return fmt.Sprintf("dbrms:lock:%d:bizid.%d", c.BkCloudId, c.ForbizId)
	}
	return fmt.Sprintf("dbrms:lock:%d:%s:bizid.%d", c.BkCloudId, c.ResourceType, c.ForbizId)
}

const (
	// SAME_SUBZONE_CROSS_SWTICH TODO
	SAME_SUBZONE_CROSS_SWTICH = "SAME_ZONE_CROSS_SWITCH"
	// SAME_SUBZONE TODO
	SAME_SUBZONE = "SAME_SUBZONE"
	// CROS_SUBZONE TODO
	CROS_SUBZONE = "CROS_SUBZONE"
	// NONE TODO
	NONE = "NONE"
)

// ApplyObjectDetail TODO
type ApplyObjectDetail struct {
	BkCloudId int               `json:"bk_cloud_id"`
	GroupMark string            `json:"group_mark" binding:"required" ` // 资源组标记
	Labels    map[string]string `json:"labels"`                         // 标签
	// 通过机型规格 或者 资源规格描述来匹配资源
	// 这两个条件是 || 关系
	DeviceClass  []string     `json:"device_class"` // 机器类型 "IT5.8XLARGE128" "SA3.2XLARGE32"
	Spec         Spec         `json:"spec"`         // 规格描述
	StorageSpecs []DiskSpec   `json:"storage_spec"`
	LocationSpec LocationSpec `json:"location_spec"` // 地域区间
	// 反亲和性 目前只有一种选项,当campus是空的时候，则此值生效
	// SAME_SUBZONE_CROSS_SWTICH: 同城同subzone跨交换机跨机架、
	// SAME_SUBZONE: 同城同subzone
	// CROS_SUBZONE：同城跨subzone
	// NONE: 无需亲和性处理
	Affinity string `json:"affinity"`
	Count    int    `json:"count" binding:"required,min=1"` // 申请数量
}

// GetDiskMatchInfo TODO
func (a *ApplyObjectDetail) GetDiskMatchInfo() (message string) {
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

// GetMessage TODO
func (a *ApplyObjectDetail) GetMessage() (message string) {
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
			if a.LocationSpec.IncludeOrExclude {
				message += fmt.Sprintf("subzoneId  must exist in the %v", a.LocationSpec.SubZoneIds)
			} else {
				message += fmt.Sprintf("subzoneId must not exist in the  %v", a.LocationSpec.SubZoneIds)
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

// GetEmptyDiskSpec TODO
func GetEmptyDiskSpec(ds []DiskSpec) (dms []DiskSpec) {
	for _, v := range ds {
		if v.MountPointIsEmpty() {
			dms = append(dms, v)
		}
	}
	return
}

// GetDiskSpecMountPoints TODO
func GetDiskSpecMountPoints(ds []DiskSpec) (mountPoints []string) {
	for _, v := range ds {
		logger.Info("disk info %v", v)
		if v.MountPointIsEmpty() {
			continue
		}
		mountPoints = append(mountPoints, path.Clean(v.MountPoint))
	}
	return
}

// Spec TODO
type Spec struct {
	Cpu MeasureRange `json:"cpu"` // cpu range
	Mem MeasureRange `json:"ram"`
}

// IsEmpty TODO
func (s Spec) IsEmpty() bool {
	return s.Cpu.IsEmpty() && s.Mem.IsEmpty()
}

// NotEmpty TODO
func (s Spec) NotEmpty() bool {
	return s.Cpu.IsNotEmpty() || s.Mem.IsNotEmpty()
}

// MeasureRange TODO
type MeasureRange struct {
	Min int `json:"min"`
	Max int `json:"max"`
}

// Iegal TODO
func (m MeasureRange) Iegal() bool {
	if m.IsNotEmpty() {
		return m.Max >= m.Min
	}
	return true
}

// MatchCpu TODO
func (cpu *MeasureRange) MatchCpu(db *gorm.DB) {
	cpu.MatchRange(db, "cpu_num")
}

// MatchTotalStorageSize TODO
func (disk *MeasureRange) MatchTotalStorageSize(db *gorm.DB) {
	disk.MatchRange(db, "total_storage_cap")
}

// MatchMem TODO
func (mem *MeasureRange) MatchMem(db *gorm.DB) {
	mem.MatchRange(db, "dram_cap")
}

// MatchRange TODO
func (m *MeasureRange) MatchRange(db *gorm.DB, col string) {
	switch {
	case m.Min > 0 && m.Max > 0:
		db.Where(col+" >= ? and "+col+" <= ?", m.Min, m.Max)
	case m.Max > 0 && m.Min <= 0:
		db.Where(col+" <= ?", m.Max)
	case m.Max <= 0 && m.Min > 0:
		db.Where(col+" >= ?", m.Min)
	}
}

// IsNotEmpty TODO
func (m MeasureRange) IsNotEmpty() bool {
	return m.Max > 0 && m.Min > 0
}

// IsEmpty TODO
func (m MeasureRange) IsEmpty() bool {
	return m.Min == 0 && m.Max == 0
}

// DiskSpec TODO
type DiskSpec struct {
	DiskType   string `json:"disk_type"`
	MinSize    int    `json:"min"`
	MaxSize    int    `json:"max"`
	MountPoint string `json:"mount_point"`
}

// LocationSpec TODO
type LocationSpec struct {
	City             string   `json:"city" validate:"required"` // 所属城市获取地域
	SubZoneIds       []string `json:"sub_zone_ids"`
	IncludeOrExclude bool     `json:"include_or_exclue"`
}

// MountPointIsEmpty TODO
func (d DiskSpec) MountPointIsEmpty() bool {
	return cmutil.IsEmpty(d.MountPoint)
}

// IsEmpty TODO
func (l LocationSpec) IsEmpty() bool {
	return cmutil.IsEmpty(l.City)
}

// SubZoneIsEmpty TODO
func (l LocationSpec) SubZoneIsEmpty() bool {
	return l.IsEmpty() || len(l.SubZoneIds) == 0
}
