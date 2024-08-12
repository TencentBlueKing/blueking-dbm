/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package manage resource manage
package manage

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/middleware"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	rf "github.com/gin-gonic/gin"
	"github.com/samber/lo"
)

// MachineResourceHandler 主机处理handler
type MachineResourceHandler struct {
	controller.BaseHandler
}

func init() {
	middleware.RequestLoggerFilter.Add("/resource/import")
	middleware.RequestLoggerFilter.Add("/resource/update")
	middleware.RequestLoggerFilter.Add("/resource/delete")
	middleware.RequestLoggerFilter.Add("/resource/batch/update")
}

// RegisterRouter 注册路由信息
func (c *MachineResourceHandler) RegisterRouter(engine *rf.Engine) {
	r := engine.Group("resource")
	{
		r.POST("/list", c.List)
		r.POST("/list/all", c.ListAll)
		r.POST("/update", c.Update)
		r.POST("/batch/update", c.BatchUpdate)
		r.POST("/delete", c.Delete)
		r.POST("/import", c.Import)
		r.POST("/mountpoints", c.GetMountPoints)
		r.POST("/disktypes", c.GetDiskTypes)
		r.POST("/subzones", c.GetSubZones)
		r.POST("/deviceclass", c.GetDeviceClass)
		r.POST("/operation/list", c.OperationInfoList)
		r.POST("/operation/create", c.RecordImportResource)
		r.POST("/spec/sum", c.SpecSum)
	}
}

// MachineDeleteInputParam 删除主机参数
type MachineDeleteInputParam struct {
	BkHostIds []int `json:"bk_host_ids"  binding:"required"`
}

// Delete 删除主机
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

// BatchUpdateMachineInput 批量编辑主机信息请求参数
type BatchUpdateMachineInput struct {
	BkHostIds      []int                    `json:"bk_host_ids"  binding:"required,dive,gt=0" `
	ForBiz         int                      `json:"for_biz"`
	RsType         string                   `json:"resource_type"`
	RackId         string                   `json:"rack_id"`
	SetBizEmpty    bool                     `json:"set_empty_biz"`
	SetRsTypeEmpty bool                     `json:"set_empty_resource_type"`
	StorageDevice  map[string]bk.DiskDetail `json:"storage_device"`
}

const (
	// EmptyArryJson empty arry json
	EmptyArryJson = "[]"
)

// BatchUpdate 批量编辑主机信息
func (c *MachineResourceHandler) BatchUpdate(r *rf.Context) {
	var input BatchUpdateMachineInput
	requestId := r.GetString("request_id")
	updateMap := make(map[string]interface{})

	if err := c.Prepare(r, &input); err != nil {
		logger.Error("Preare Error %s", err.Error())
		return
	}

	// update for biz
	if input.ForBiz > 0 {
		updateMap["dedicated_biz"] = input.ForBiz
	}

	// update resource type
	if lo.IsNotEmpty(input.RsType) {
		updateMap["rs_type"] = input.RsType
	}

	// update disk
	if len(input.StorageDevice) > 0 {
		storageJson, err := json.Marshal(input.StorageDevice)
		if err != nil {
			logger.Error(fmt.Sprintf("conver resource types Failed,Error:%s", err.Error()))
			c.SendResponse(r, err, requestId, err.Error())
			return
		}
		updateMap["storage_device"] = storageJson
	}

	// update rack id
	if cmutil.IsNotEmpty(input.RackId) {
		updateMap["rack_id"] = input.RackId
	}

	// do update
	err := model.DB.Self.Table(model.TbRpDetailName()).Select("dedicated_biz", "rs_type", "storage_device", "rack_id").
		Where("bk_host_id in (?)", input.BkHostIds).Updates(updateMap).Error
	if err != nil {
		c.SendResponse(r, err, requestId, err.Error())
		return
	}

	// return respone
	c.SendResponse(r, nil, "ok", requestId)
}

// MachineResourceInputParam 多个不同的主句的编辑的不同的参数
type MachineResourceInputParam struct {
	Data []MachineResource `json:"data" binding:"required,dive,gt=0"`
}

// MachineResource 主机参数
type MachineResource struct {
	BkHostID      int                      `json:"bk_host_id" binding:"required"`
	Labels        map[string]string        `json:"labels"`
	ForBiz        int                      `json:"for_biz"`
	RsType        string                   `json:"resource_type"`
	StorageDevice map[string]bk.DiskDetail `json:"storage_device"`
}

// Update 编辑主机信息
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
		if v.ForBiz > 0 {
			updateMap["dedicated_biz"] = v.ForBiz
		}
		if lo.IsNotEmpty(v.RsType) {
			updateMap["rs_type"] = v.RsType
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
		err := tx.Model(&model.TbRpDetail{}).Table(model.TbRpDetailName()).Select("dedicated_biz", "rs_type",
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

// GetMountPoints get disk mount points
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

// GetDiskTypes get disk types
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

// GetSubZoneParam get subzones param
type GetSubZoneParam struct {
	LogicCitys []string `json:"citys"`
}

// GetSubZones get subzones
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

// GetDeviceClass 获取机型
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
