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
	"encoding/json"
	"fmt"
	"strings"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	rf "github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// MachineResourceHandler TODO
type MachineResourceHandler struct {
	controller.BaseHandler
}

// RegisterRouter TODO
func (c *MachineResourceHandler) RegisterRouter(engine *rf.Engine) {
	r := engine.Group("resource")
	{
		r.POST("/list", c.List)
		r.POST("/list/all", c.ListAll)
		r.POST("/update", c.Update)
		r.POST("/delete", c.Delete)
		r.POST("/import", c.Import)
		r.POST("/mountpoints", c.GetMountPoints)
		r.POST("/disktypes", c.GetDiskTypes)
		r.POST("/subzones", c.GetSubZones)
		r.POST("/deviceclass", c.GetDeviceClass)
		r.POST("/operation/list", c.OperationInfoList)
	}
}

// MachineResourceGetterInputParam TODO
type MachineResourceGetterInputParam struct {
	// 专用业务Ids
	ForBizs     []int              `json:"for_bizs"`
	City        []string           `json:"city"`
	SubZones    []string           `json:"subzones"`
	DeviceClass []string           `json:"device_class"`
	Labels      map[string]string  `json:"labels"`
	Hosts       []string           `json:"hosts"`
	BkCloudIds  []int              `json:"bk_cloud_ids"`
	RsTypes     []string           `json:"resource_types"`
	MountPoint  string             `json:"mount_point"`
	Cpu         apply.MeasureRange `json:"cpu"`
	Mem         apply.MeasureRange `json:"mem"`
	Disk        apply.MeasureRange `json:"disk"`
	DiskType    string             `json:"disk_type"`
	// true,false,""
	GseAgentAlive string `json:"gse_agent_alive"`
	Limit         int    `json:"limit"`
	Offset        int    `json:"offset"`
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

// List TODO
func (c *MachineResourceHandler) List(r *rf.Context) {
	var input MachineResourceGetterInputParam
	if c.Prepare(r, &input) != nil {
		return
	}
	requestId := r.GetString("request_id")
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
	if err := db.Scan(&data).Error; err != nil {
		c.SendResponse(r, errno.ErrDBQuery.AddErr(err), requestId, err.Error())
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count}, requestId)
}

func (c *MachineResourceGetterInputParam) queryBs(db *gorm.DB) {
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
		db.Where(model.JSONQuery("rs_types").Contains(c.RsTypes))
	}
	if c.Cpu.Iegal() && c.Cpu.IsNotEmpty() {
		db.Where("cpu_num >= ? and cpu_num <= ?", c.Cpu.Min, c.Cpu.Max)
	}
	if c.Mem.Iegal() && c.Mem.IsNotEmpty() {
		db.Where("dram_cap >= ? and dram_cap <= ?", c.Mem.Min, c.Mem.Max)
	}
	if c.Disk.Iegal() && c.Disk.IsNotEmpty() {
		db.Where("total_storage_cap >= ? and total_storage_cap <= ? ", c.Disk.Min, c.Disk.Max)
	}
	if cmutil.IsNotEmpty(c.MountPoint) {
		if cmutil.IsNotEmpty(c.DiskType) {
			db.Where(model.JSONQuery("storage_device").Equals(c.DiskType, c.MountPoint, "disk_type"))
		} else {
			db.Where(model.JSONQuery("storage_device").KeysContains([]string{c.MountPoint}))
		}
	} else {
		if cmutil.IsNotEmpty(c.DiskType) {
			db.Where(model.JSONQuery("storage_device").SubValContains(c.DiskType, "disk_type"))
		}
	}
	db.Where("status = ? ", model.Unused)
	if len(c.City) > 0 {
		db.Where(" city in (?) ", c.City)
	}
	if len(c.SubZones) > 0 {
		db.Where(" sub_zone in (?) ", c.SubZones)
	}
	if len(c.DeviceClass) > 0 {
		db.Where("device_class in ? ", c.DeviceClass)
	}
	if len(c.ForBizs) > 0 {
		db.Where(model.JSONQuery("dedicated_bizs").Contains(cmutil.IntSliceToStrSlice(c.ForBizs)))
	}
	if len(c.Labels) > 0 {
		for key, v := range c.Labels {
			db.Where("json_contains(label,json_object(?,?))", key, v)
		}
	}
}

// Delete TODO
func (c *MachineResourceHandler) Delete(r *rf.Context) {
	var input MachineDeleteInputParam
	if err := c.Prepare(r, &input); err != nil {
		logger.Error("Preare Error %s", err.Error())
		return
	}
	requestId := r.GetString("request_id")
	affect_row, err := model.DeleteTbRpDetail(input.BkHostIds)
	if err != nil {
		logger.Error("failed to delete data:%s", err.Error())
		c.SendResponse(r, err, nil, requestId)
		return
	}
	if affect_row == 0 {
		c.SendResponse(r, fmt.Errorf("no data was deleted"), nil, requestId)
		return
	}
	c.SendResponse(r, nil, requestId, "Delete Success")
}

// Update TODO
func (c *MachineResourceHandler) Update(r *rf.Context) {
	var input MachineResourceInputParam
	requestId := r.GetString("request_id")
	if err := c.Prepare(r, &input); err != nil {
		logger.Error("Preare Error %s", err.Error())
		return
	}
	logger.Debug(fmt.Sprintf("get params %v", input.Data))
	tx := model.DB.Self.Begin()
	for _, v := range input.Data {
		updateMap := make(map[string]interface{})
		if len(v.Labels) > 0 {
			l, err := cmutil.ConverMapToJsonStr(v.Labels)
			if err != nil {
				logger.Error(fmt.Sprintf("ConverMapToJsonStr Failed %s", err.Error()))
			}
			updateMap["lable"] = l
		}
		if len(v.ForBizs) > 0 {
			bizJson, err := json.Marshal(cmutil.IntSliceToStrSlice(v.ForBizs))
			if err != nil {
				logger.Error(fmt.Sprintf("conver biz json Failed,Error:%s", err.Error()))
				c.SendResponse(r, err, requestId, err.Error())
				return
			}
			updateMap["dedicated_bizs"] = bizJson
		}
		if len(v.RsTypes) > 0 {
			rstypes, err := json.Marshal(v.RsTypes)
			if err != nil {
				logger.Error(fmt.Sprintf("conver resource types Failed,Error:%s", err.Error()))
				c.SendResponse(r, err, requestId, err.Error())
				return
			}
			updateMap["rs_types"] = rstypes
		}
		if len(v.StorageDevice) > 0 {
			storageJson, err := json.Marshal(v.StorageDevice)
			if err != nil {
				logger.Error(fmt.Sprintf("conver resource types Failed,Error:%s", err.Error()))
				c.SendResponse(r, err, requestId, err.Error())
				return
			}
			updateMap["storage_device"] = storageJson
		}
		err := tx.Model(&model.TbRpDetail{}).Table(model.TbRpDetailName()).Select("dedicated_bizs", "rs_types",
			"label").Where("bk_host_id=?", v.BkHostID).Updates(updateMap).Error
		if err != nil {
			tx.Rollback()
			logger.Error(fmt.Sprintf("conver resource types Failed,Error:%s", err.Error()))
			c.SendResponse(r, err, requestId, err.Error())
			return
		}
	}
	if err := tx.Commit().Error; err != nil {
		c.SendResponse(r, err, requestId, err.Error())
		return
	}
	c.SendResponse(r, nil, requestId, "Save Success")
}

// MachineDeleteInputParam TODO
type MachineDeleteInputParam struct {
	BkHostIds []int `json:"bk_host_ids"  binding:"required"`
}

// MachineResourceInputParam TODO
type MachineResourceInputParam struct {
	Data []MachineResource `json:"data" binding:"required,dive,gt=0"`
}

// MachineResource TODO
type MachineResource struct {
	BkHostID      int                      `json:"bk_host_id" binding:"required"`
	Labels        map[string]string        `json:"labels"`
	ForBizs       []int                    `json:"for_bizs"`
	RsTypes       []string                 `json:"resource_types"`
	StorageDevice map[string]bk.DiskDetail `json:"storage_device"`
}

// GetMountPoints TODO
func (c MachineResourceHandler) GetMountPoints(r *rf.Context) {
	db := model.DB.Self.Table(model.TbRpDetailName())
	var rs []json.RawMessage
	if err := db.Select("json_keys(storage_device)").Where("JSON_LENGTH(storage_device) > 0").Find(&rs).Error; err != nil {
		logger.Error("get mountpoints failed %s", err.Error())
		c.SendResponse(r, err, err.Error(), "")
		return
	}
	var mountpoints []string
	for _, v := range rs {
		var mp []string
		if err := json.Unmarshal(v, &mp); err != nil {
			logger.Error("unmarshal failed %s", err.Error())
			c.SendResponse(r, err, err.Error(), "")
			return
		}
		if len(mp) > 0 {
			mountpoints = append(mountpoints, mp...)
		}
	}
	c.SendResponse(r, nil, cmutil.RemoveDuplicate(mountpoints), r.GetString("request_id"))
}

// GetDiskTypes TODO
func (c MachineResourceHandler) GetDiskTypes(r *rf.Context) {
	db := model.DB.Self.Table(model.TbRpDetailName())
	var rs []json.RawMessage
	err := db.Select("json_extract(storage_device,'$.*.\"disk_type\"')").Where("JSON_LENGTH(storage_device) > 0").
		Find(&rs).Error
	if err != nil {
		logger.Error("get DiskType failed %s", err.Error())
		c.SendResponse(r, err, err.Error(), "")
		return
	}
	var diskTypes []string
	for _, v := range rs {
		var mp []string
		if err := json.Unmarshal(v, &mp); err != nil {
			logger.Error("unmarshal failed %s", err.Error())
			c.SendResponse(r, err, err.Error(), "")
			return
		}
		if len(mp) > 0 {
			diskTypes = append(diskTypes, mp...)
		}
	}
	c.SendResponse(r, nil, cmutil.RemoveDuplicate(diskTypes), r.GetString("request_id"))
}

// GetSubZoneParam TODO
type GetSubZoneParam struct {
	LogicCitys []string `json:"citys"`
}

// GetSubZones TODO
func (c MachineResourceHandler) GetSubZones(r *rf.Context) {
	var input GetSubZoneParam
	if c.Prepare(r, &input) != nil {
		return
	}
	var subZones []string
	db := model.DB.Self.Table(model.TbRpDetailName())
	err := db.Distinct("sub_zone").Where("city in ? ", input.LogicCitys).Find(&subZones).Error
	if err != nil {
		c.SendResponse(r, err, "", err.Error())
		return
	}
	c.SendResponse(r, nil, subZones, r.GetString("request_id"))
}

// GetDeviceClass TODO
func (c MachineResourceHandler) GetDeviceClass(r *rf.Context) {
	var class []string
	db := model.DB.Self.Table(model.TbRpDetailName())
	err := db.Distinct("device_class").Where("device_class !=''").Find(&class).Error
	if err != nil {
		c.SendResponse(r, err, "", err.Error())
		return
	}
	c.SendResponse(r, nil, class, r.GetString("request_id"))
}
