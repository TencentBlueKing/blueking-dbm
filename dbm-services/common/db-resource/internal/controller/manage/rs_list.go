/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"fmt"
	"path"
	"strings"

	rf "github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"
)

// MachineResourceGetterInputParam TODO
type MachineResourceGetterInputParam struct {
	// 专用业务Ids
	ForBiz        *int              `json:"for_biz"`       // 后续删除
	RsType        *string           `json:"resource_type"` // 后续删除
	ForBizs       []int             `json:"for_bizs"`
	RsTypes       []string          `json:"resource_types"`
	City          []string          `json:"city"`
	SubZoneIds    []string          `json:"subzone_ids"`
	DeviceClass   []string          `json:"device_class"`
	Labels        []string          `json:"labels"`
	Hosts         []string          `json:"hosts"`
	BkCloudIds    []int             `json:"bk_cloud_ids"`
	MountPoint    string            `json:"mount_point"`
	Cpu           meta.MeasureRange `json:"cpu"`
	Mem           meta.MeasureRange `json:"mem"`
	Disk          meta.MeasureRange `json:"disk"`
	DiskType      string            `json:"disk_type"`
	OsType        string            `json:"os_type"`
	OsNames       []string          `json:"os_names"`
	ExcludeOsName bool              `json:"exclude_os_name"`
	StorageSpecs  []meta.DiskSpec   `json:"storage_spec"`
	CreateTime    string            `json:"create_time"`
	EmptyLabels   bool              `json:"empty_labels"`
	// true,false,""
	GseAgentAlive string `json:"gse_agent_alive"`
	Limit         int    `json:"limit"`
	Offset        int    `json:"offset"`
}

// List TODO
func (c *MachineResourceHandler) List(r *rf.Context) {
	var input MachineResourceGetterInputParam
	var count int64

	if c.Prepare(r, &input) != nil {
		return
	}
	if err := input.paramCheck(); err != nil {
		c.SendResponse(r, errno.ErrErrInvalidParam.AddErr(err), nil)
		return
	}
	db := model.DB.Self.Table(model.TbRpDetailName())
	if err := input.queryBs(db); err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	if err := db.Count(&count).Error; err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	if input.Limit > 0 {
		db = db.Offset(input.Offset).Limit(input.Limit)
	}
	var data []model.TbRpDetail
	if err := db.Find(&data).Error; err != nil {
		c.SendResponse(r, errno.ErrDBQuery.AddErr(err), err.Error())
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count})
}

func (c *MachineResourceGetterInputParam) paramCheck() (err error) {
	if !c.Cpu.Legal() {
		return fmt.Errorf("非法参数 cpu min:%d,max:%d", c.Cpu.Min, c.Cpu.Max)
	}
	if !c.Mem.Legal() {
		return fmt.Errorf("非法参数 mem min:%d,max:%d", c.Mem.Min, c.Mem.Max)
	}
	return nil
}

// matchStorageSpecs 匹配磁盘
func (c *MachineResourceGetterInputParam) matchStorageSpecs(db *gorm.DB) {
	if len(c.StorageSpecs) > 0 {
		// 使用与 MatchStorage 相同的批量处理逻辑
		allSpecMinIsZero := false
		AndQ := []interface{}{}

		for _, d := range c.StorageSpecs {
			if cmutil.IsEmpty(d.MountPoint) {
				continue
			}
			mp := path.Clean(d.MountPoint)
			if cmutil.IsNotEmpty(d.DiskType) {
				AndQ = append(AndQ, model.JSONQuery("storage_device").Equals(d.DiskType, mp, "disk_type"))
			}
			logger.Info("storage spec is %v", d)
			switch {
			case d.MaxSize > 0:
				AndQ = append(AndQ, model.JSONQuery("storage_device").NumRange(d.MinSize, d.MaxSize, mp, "size"))
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
				condStr = "(" + condStr + ") OR ( storage_device IS NULL OR JSON_LENGTH(storage_device) = 0)"
			}
			db.Where(condStr, AndQ...)
		} else if allSpecMinIsZero {
			// 没有其他条件时，只匹配空设备
			db.Where("storage_device IS NULL OR JSON_LENGTH(storage_device) = 0")
		}
	} else {
		// 保持原有的 else 分支逻辑不变（向后兼容旧参数）
		if cmutil.IsNotEmpty(c.MountPoint) {
			mp := path.Clean(c.MountPoint)
			if cmutil.IsNotEmpty(c.DiskType) {
				db.Where(model.JSONQuery("storage_device").Equals(c.DiskType, mp, "disk_type"))
			}
			db.Where(model.JSONQuery("storage_device").NumRange(c.Disk.Min, c.Disk.Max, mp, "size"))
			return
		} else if cmutil.IsNotEmpty(c.DiskType) {
			db.Where(model.JSONQuery("storage_device").SubValContains(c.DiskType, "disk_type"))
		}
		c.Disk.MatchTotalDataStorageSize(db)
	}
}

func (c *MachineResourceGetterInputParam) getRealCities() (realCities []string, err error) {
	for _, logicCity := range c.City {
		real_cities, err := dbmapi.GetIdcCityByLogicCity(logicCity)
		if err != nil {
			logger.Error("from %s get real cites failed %s", logicCity, err.Error())
			return nil, err
		}
		realCities = append(realCities, real_cities...)
	}
	logger.Info("get real cites %v", realCities)
	return
}

func (c *MachineResourceGetterInputParam) matchSpec(db *gorm.DB) {
	if len(c.DeviceClass) > 0 {
		switch {
		case c.Cpu.IsEmpty() && c.Mem.IsEmpty():
			db.Where(" device_class in (?) ", c.DeviceClass)
		case c.Cpu.IsEmpty() && c.Mem.IsNotEmpty():
			db.Where("? or device_class in (?)", c.Mem.MatchMemBuilder(), c.DeviceClass)
		case c.Cpu.IsNotEmpty() && c.Mem.IsEmpty():
			db.Where("? or device_class in (?)", c.Cpu.MatchCpuBuilder(), c.DeviceClass)
		case c.Cpu.IsNotEmpty() && c.Mem.IsNotEmpty():
			db.Where("( ? and  ? ) or device_class in (?)", c.Cpu.MatchCpuBuilder(), c.Mem.MatchMemBuilder(), c.DeviceClass)
		}
		return
	}
	c.Cpu.MatchCpu(db)
	c.Mem.MatchMem(db)
}
func (c *MachineResourceGetterInputParam) queryBs(db *gorm.DB) (err error) {
	db.Where("status = ? ", model.Unused)
	if len(c.Hosts) > 0 {
		db.Where("ip in (?)", c.Hosts)
	}
	switch strings.TrimSpace(strings.ToLower(c.GseAgentAlive)) {
	case "true":
		db.Where("gse_agent_status_code = ?  ", bk.GseAlive)
	case "false":
		db.Where("gse_agent_status_code != ?  ", bk.GseAlive)
	}
	if len(c.BkCloudIds) > 0 {
		db.Where("bk_cloud_id in (?) ", c.BkCloudIds)
	}
	if c.RsType != nil {
		db.Where("rs_type = ? ", c.RsType)
	}
	if c.ForBiz != nil {
		db.Where("dedicated_biz = ?", c.ForBiz)
	}
	if len(c.RsTypes) > 0 {
		db.Where("rs_type in (?) ", c.RsTypes)
	}
	if len(c.ForBizs) > 0 {
		db.Where("dedicated_biz in (?) ", c.ForBizs)
	}
	c.matchSpec(db)
	c.matchStorageSpecs(db)
	if len(c.City) > 0 {
		realCities, err := c.getRealCities()
		if err != nil {
			return err
		}
		db.Where(" city in (?) ", realCities)
	}
	if len(c.SubZoneIds) > 0 {
		db.Where(" sub_zone_id in (?) ", c.SubZoneIds)
	}
	if len(c.Labels) > 0 {
		db.Where(model.JSONQuery("labels").JointOrContains(c.Labels))
	} else {
		if c.EmptyLabels {
			db.Where(" JSON_TYPE(labels) = 'NULL' or JSON_TYPE(labels) is null OR JSON_LENGTH(labels) < 1 ")
		}
	}

	if lo.IsNotEmpty(c.OsType) {
		db.Where("os_type = ?", c.OsType)
	}
	if len(c.OsNames) > 0 {
		if c.ExcludeOsName {
			db.Where("os_name not in (?)", c.OsNames)
		} else {
			db.Where("os_name in (?)", c.OsNames)
		}
	}
	if lo.IsNotEmpty(c.CreateTime) {
		db.Where("create_time >= ?", c.CreateTime)
	}
	db.Order("create_time desc")
	return nil
}

// ListAll TODO
func (c *MachineResourceHandler) ListAll(r *rf.Context) {
	// requestId := r.GetString("request_id")
	var data []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName()).Where("status in (?)", []string{model.Unused, model.Prepoccupied,
		model.Preselected})
	err := db.Scan(&data).Error
	if err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	var count int64
	if err := db.Count(&count).Error; err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count})
}

// ListOsName returns all os names
func (c *MachineResourceHandler) ListOsName(r *rf.Context) {
	// requestId := r.GetString("request_id")
	var data []string
	db := model.DB.Self.Table(model.TbRpDetailName()).Distinct("os_name")
	err := db.Scan(&data).Error
	if err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	var count int64
	if err := db.Count(&count).Error; err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	c.SendResponse(r, nil, data)
}
