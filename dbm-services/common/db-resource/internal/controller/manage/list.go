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
	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"
)

// MachineResourceGetterInputParam TODO
type MachineResourceGetterInputParam struct {
	// 专用业务Ids
	ForBizs      []int              `json:"for_bizs"`
	City         []string           `json:"city"`
	SubZones     []string           `json:"subzones"`
	DeviceClass  []string           `json:"device_class"`
	Labels       map[string]string  `json:"labels"`
	Hosts        []string           `json:"hosts"`
	BkCloudIds   []int              `json:"bk_cloud_ids"`
	RsTypes      []string           `json:"resource_types"`
	MountPoint   string             `json:"mount_point"`
	Cpu          apply.MeasureRange `json:"cpu"`
	Mem          apply.MeasureRange `json:"mem"`
	Disk         apply.MeasureRange `json:"disk"`
	DiskType     string             `json:"disk_type"`
	StorageSpecs []apply.DiskSpec   `json:"storage_spec"`
	// true,false,""
	GseAgentAlive string `json:"gse_agent_alive"`
	Limit         int    `json:"limit"`
	Offset        int    `json:"offset"`
}

// List TODO
func (c *MachineResourceHandler) List(r *rf.Context) {
	var input MachineResourceGetterInputParam
	if c.Prepare(r, &input) != nil {
		return
	}
	requestId := r.GetString("request_id")
	if err := input.paramCheck(); err != nil {
		c.SendResponse(r, errno.ErrErrInvalidParam.AddErr(err), nil, requestId)
		return
	}
	db := model.DB.Self.Table(model.TbRpDetailName())
	input.queryBs(db)
	var count int64
	if err := db.Count(&count).Error; err != nil {
		c.SendResponse(r, err, requestId, err.Error())
		return
	}
	if input.Limit > 0 {
		db = db.Offset(input.Offset).Limit(input.Limit)
	}
	var data []model.TbRpDetail
	if err := db.Find(&data).Error; err != nil {
		c.SendResponse(r, errno.ErrDBQuery.AddErr(err), requestId, err.Error())
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count}, requestId)
}

func (c *MachineResourceGetterInputParam) paramCheck() (err error) {
	if !c.Cpu.Iegal() {
		return fmt.Errorf("非法参数 cpu min:%d,max:%d", c.Cpu.Min, c.Cpu.Max)
	}
	if !c.Mem.Iegal() {
		return fmt.Errorf("非法参数 mem min:%d,max:%d", c.Mem.Min, c.Mem.Max)
	}
	return nil
}

// matchStorageSpecs TODO
func (c *MachineResourceGetterInputParam) matchStorageSpecs(db *gorm.DB) {
	if len(c.StorageSpecs) > 0 {
		for _, d := range c.StorageSpecs {
			if cmutil.IsNotEmpty(d.MountPoint) {
				mp := path.Clean(d.MountPoint)
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
	} else {
		c.Disk.MatchTotalStorageSize(db)
		if cmutil.IsNotEmpty(c.MountPoint) {
			mp := path.Clean(c.MountPoint)
			if cmutil.IsNotEmpty(c.DiskType) {
				db.Where(model.JSONQuery("storage_device").Equals(c.DiskType, mp, "disk_type"))
			} else {
				db.Where(model.JSONQuery("storage_device").KeysContains([]string{mp}))
			}
		} else {
			if cmutil.IsNotEmpty(c.DiskType) {
				db.Where(model.JSONQuery("storage_device").SubValContains(c.DiskType, "disk_type"))
			}
		}
	}
}

func (c *MachineResourceGetterInputParam) queryBs(db *gorm.DB) {
	db.Where("status = ? ", model.Unused)
	if len(c.Hosts) > 0 {
		db.Where("ip in (?)", c.Hosts)
		return
	}
	switch strings.TrimSpace(strings.ToLower(c.GseAgentAlive)) {
	case "true":
		db.Where("gse_agent_status_code = ?  ", bk.GSE_AGENT_OK)
	case "false":
		db.Where("gse_agent_status_code != ?  ", bk.GSE_AGENT_OK)
	}
	if len(c.BkCloudIds) > 0 {
		db.Where("bk_cloud_id in (?) ", c.BkCloudIds)
	}
	if len(c.RsTypes) > 0 {
		// 如果参数["all"],表示选择没有任何资源类型标签的资源
		if c.RsTypes[0] == "all" {
			db.Where("JSON_LENGTH(rs_types) <= 0")
		} else {
			db.Where("(?)", model.JSONQuery("rs_types").JointOrContains(c.RsTypes))
		}
	}
	c.Cpu.MatchCpu(db)
	c.Mem.MatchMem(db)
	c.matchStorageSpecs(db)
	if len(c.City) > 0 {
		db.Where(" city in (?) ", c.City)
	}
	if len(c.SubZones) > 0 {
		db.Where(" sub_zone in (?) ", c.SubZones)
	}
	if len(c.DeviceClass) > 0 {
		db.Where("device_class in (?) ", c.DeviceClass)
	}
	if len(c.ForBizs) > 0 {
		// 如果参数[0],表示选择没有任何业务标签的资源
		if c.ForBizs[0] == 0 {
			db.Where("JSON_LENGTH(dedicated_bizs) <= 0")
		} else {
			db.Where("(?)", model.JSONQuery("dedicated_bizs").JointOrContains(cmutil.IntSliceToStrSlice(c.ForBizs)))
		}
	}

	db.Order("create_time desc")
}

// ListAll TODO
func (c *MachineResourceHandler) ListAll(r *rf.Context) {
	requestId := r.GetString("request_id")
	var data []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName()).Where("status in (?)", []string{model.Unused, model.Prepoccupied,
		model.Preselected})
	err := db.Scan(&data).Error
	if err != nil {
		c.SendResponse(r, err, requestId, err.Error())
		return
	}
	var count int64
	if err := db.Count(&count).Error; err != nil {
		c.SendResponse(r, err, requestId, err.Error())
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count}, requestId)
}
