/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package controller TODO
package controller

import (
	"encoding/json"
	"fmt"
	"net/http"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/db-resource/internal/svr/yunti"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
)

// BaseHandler base handler
type BaseHandler struct {
	RequestId string
}

// Response http respone
type Response struct {
	Code      int         `json:"code"`
	Message   string      `json:"message"`
	Data      interface{} `json:"data"`
	RequestId string      `json:"request_id"`
}

// Prepare before request prepared
func (c *BaseHandler) Prepare(r *gin.Context, schema interface{}) error {
	requestId := r.GetString("request_id")
	if cmutil.IsEmpty(requestId) {
		err := fmt.Errorf("get request id error ~")
		c.SendResponse(r, err, nil)
		return err
	}
	c.RequestId = requestId
	if err := r.ShouldBind(&schema); err != nil {
		logger.Error("ShouldBind Failed %s", err.Error())
		c.SendResponse(r, err, nil)
		return err
	}
	logger.Info("param is %v", schema)
	return nil
}

// SendResponse retrnurns a response
func (c *BaseHandler) SendResponse(r *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)
	r.JSON(http.StatusOK, Response{
		Code:      code,
		Message:   message,
		Data:      data,
		RequestId: c.RequestId,
	})
}

// BackStageHandler BackStageHandler
type BackStageHandler struct {
	BaseHandler
}

// RegisterRouter RegisterRouter
func (c *BackStageHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("background")
	{
		r.POST("/cc/module/check", c.RunModuleCheck)
		r.POST("/cc/async", c.RunAsyncCmdb)
		r.POST("/cc/sync/os/info", c.SyncOsInfo)
		r.POST("/cc/sync/netdevice", c.FlushNetDeviceInfo)
		r.POST("/cc/sync/disk", c.FlushDiskInfo)
	}
}

// RunModuleCheck run module check
func (c BackStageHandler) RunModuleCheck(r *gin.Context) {
	err := task.InspectCheckResource()
	if err != nil {
		logger.Error("inspectCheckResource failed %v", err)
	}
	c.SendResponse(r, nil, "Check Success")
}

// RunAsyncCmdb async from cmdb
func (c BackStageHandler) RunAsyncCmdb(r *gin.Context) {
	err := task.AsyncResourceHardInfo()
	if err != nil {
		logger.Error("asyncResourceHardInfo failed %v", err)
	}
	c.SendResponse(r, nil, "async success")
}

// SyncOsInfo sync os info
func (c BackStageHandler) SyncOsInfo(r *gin.Context) {
	err := task.SyncOsNameInfo()
	if err != nil {
		logger.Error("SyncOsNameInfo failed %v", err)
	}
	c.SendResponse(r, nil, "async success")
}

// FlushNetDeviceInfo flush net device info
func (c BackStageHandler) FlushNetDeviceInfo(r *gin.Context) {
	err := task.FlushNetDeviceInfo()
	if err != nil {
		logger.Error("flush failed %v", err)
	}
	c.SendResponse(r, nil, "success")
}

// FlushDiskInfo 刷新磁盘信息
func (c BackStageHandler) FlushDiskInfo(r *gin.Context) {
	var rsList []model.TbRpDetail
	err := model.DB.Self.Table(model.TbRpDetailName()).Find(&rsList).Error
	if err != nil {
		c.SendResponse(r, fmt.Errorf("query resource detail failed %w", err), nil)
	}
	for _, rs := range rsList {
		var dks map[string]bk.DiskDetail
		logger.Info("flush disk info %s ", rs.IP)
		if err = json.Unmarshal(rs.StorageDevice, &dks); err != nil {
			logger.Error("unmarshal disk info failed %v", err)
			continue
		}
		resp, err := config.AppConfig.Yunti.QueryCVMInstances([]string{rs.IP})
		if err != nil {
			logger.Error("queryCVMInstances failed %v", err)
			continue
		}
		if len(resp.Result.Data) == 0 {
			continue
		}
		cvmdiskList := resp.Result.Data[0].DatadiskList
		if len(cvmdiskList) == 0 {
			continue
		}
		diskdetailMap := lo.SliceToMap(cvmdiskList, func(d yunti.CvmDataDisk) (string, yunti.CvmDataDisk) {
			return d.DiskId, d
		})
		rebuildDks := make(map[string]bk.DiskDetail)
		for mp, dk := range dks {
			dd := dk
			if detail, exist := diskdetailMap[dk.DiskId]; exist {
				dd.Size = detail.DiskSize
				dd.DiskType = model.TransferCloudDiskType(detail.DiskType)
			}
			rebuildDks[mp] = dd
		}
		r, err := json.Marshal(rebuildDks)
		if err != nil {
			logger.Error("marshal failed %v", err)
			continue
		}
		rs.StorageDevice = []byte(r)
		if err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id = ?", rs.BkHostID).Updates(rs).
			Error; err != nil {
			logger.Error("update failed %v", err)
		}
	}
	c.SendResponse(r, nil, "success")
}
