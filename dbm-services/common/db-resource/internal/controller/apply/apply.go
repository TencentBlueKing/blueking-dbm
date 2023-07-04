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
	"time"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/lock"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
)

// ApplyHandler TODO
type ApplyHandler struct {
	controller.BaseHandler
}

// RegisterRouter TODO
//
//	@receiver c
//	@param engine
func (c *ApplyHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("resource")
	{
		r.POST("/apply", c.ApplyResource)
		r.POST("/pre-apply", c.PreApplyResource)
		r.POST("/confirm/apply", c.ConfirmApply)
	}
}

// ConfirmApplyParam TODO
type ConfirmApplyParam struct {
	RequestId string `json:"request_id" binding:"required"`
	HostIds   []int  `json:"host_ids" binding:"gt=0,dive,required" `
}

// ConfirmApply TODO
func (c *ApplyHandler) ConfirmApply(r *gin.Context) {
	var param ConfirmApplyParam
	if c.Prepare(r, &param) != nil {
		return
	}
	requestId := r.GetString("request_id")
	hostIds := cmutil.RemoveDuplicate(param.HostIds)
	var cnt int64
	err := model.DB.Self.Table(model.TbRpApplyDetailLogName()).Where("request_id = ?", param.RequestId).Count(&cnt).Error
	if err != nil {
		logger.Error("use request id %s,query apply resouece failed %s", param.RequestId, err.Error())
		c.SendResponse(r, fmt.Errorf("%w", err), "use request id search applyed resource failed", requestId)
		return
	}
	if len(hostIds) != int(cnt) {
		c.SendResponse(r, fmt.Errorf("need return resource count is %d,but use request id only found total count %d",
			len(hostIds), cnt), requestId, "")
		return
	}
	var rs []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id in (?) and status != ? ", hostIds,
		model.Prepoccupied).Find(&rs).Error
	if err != nil {
		c.SendResponse(r, err, err.Error(), requestId)
		return
	}
	if len(rs) > 0 {
		var errMsg string
		for _, v := range rs {
			errMsg += fmt.Sprintf("%s:%s\n", v.IP, v.Status)
		}
		c.SendResponse(r, fmt.Errorf("the following example:%s,abnormal state", errMsg), "", requestId)
		return
	}
	// update to used status
	err = cmutil.Retry(
		cmutil.RetryConfig{Times: 3, DelayTime: 1 * time.Second},
		func() error {
			return model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id in (?) ", hostIds).Update("status",
				model.Used).Error
		},
	)
	if err != nil {
		c.SendResponse(r, err, err.Error(), requestId)
		return
	}
	uerr := model.DB.Self.Table(model.TbRpOperationInfoTableName()).Where("request_id = ?",
		param.RequestId).Update("status", model.Used).Error
	if uerr != nil {
		logger.Warn("update tb_rp_operation_info failed %s ", uerr.Error())
	}
	archive(hostIds)
	c.SendResponse(r, nil, "successful", requestId)
}

func archive(bkHostIds []int) {
	var rs []model.TbRpDetail
	err := model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id in (?) and status = ? ", bkHostIds,
		model.Used).Find(&rs).Error
	if err != nil {
		logger.Error("query used resource failed %s", err.Error())
		return
	}
	for _, v := range rs {
		task.ArchiverResourceChan <- v.ID
	}
}

// ApplyResource TODO
func (c *ApplyHandler) ApplyResource(r *gin.Context) {
	c.ApplyBase(r, model.Used)
}

// PreApplyResource TODO
func (c *ApplyHandler) PreApplyResource(r *gin.Context) {
	c.ApplyBase(r, model.Prepoccupied)
}

func newLocker(key string, requestId string) *lock.SpinLock {
	return lock.NewSpinLock(&lock.RedisLock{Name: key, RandKey: requestId, Expiry: 120 * time.Second}, 60,
		350*time.Millisecond)
}

// ApplyBase TODO
func (c *ApplyHandler) ApplyBase(r *gin.Context, mode string) {
	task.RuningTask <- struct{}{}
	defer func() { <-task.RuningTask }()
	logger.Info("start apply resource ... ")
	var param apply.ApplyRequestInputParam
	var pickers []*apply.PickerObject
	var err error
	var requestId string
	if c.Prepare(r, &param) != nil {
		return
	}
	requestId = r.GetString("request_id")
	if err := param.ParamCheck(); err != nil {
		c.SendResponse(r, err, err.Error(), requestId)
		return
	}
	// get the resource lock if it is dry run you do not need to acquire it
	if !param.DryRun {
		lock := newLocker(param.LockKey(), requestId)
		if err := lock.Lock(); err != nil {
			c.SendResponse(r, err, err.Error(), requestId)
			return
		}
		defer func() {
			if err := lock.Unlock(); err != nil {
				logger.Error(fmt.Sprintf("unlock failed %s", err.Error()))
				return
			}
		}()
	}
	defer func() {
		apply.RollBackAllInstanceUnused(pickers)
	}()
	pickers, err = apply.CycleApply(param)
	if err != nil {
		logger.Error("apply machine failed %s", err.Error())
		c.SendResponse(r, err, err.Error(), requestId)
		return
	}
	if param.DryRun {
		c.SendResponse(r, nil, map[string]interface{}{"check_success": true}, requestId)
		return
	}
	data, err := apply.LockReturnPickers(pickers, mode)
	if err != nil {
		c.SendResponse(r, err, nil, requestId)
		return
	}
	logger.Info(fmt.Sprintf("The %s, will return %d machines", requestId, len(data)))
	task.ApplyResponeLogChan <- task.ApplyResponeLogItem{
		RequestId: requestId,
		Data:      data,
	}
	task.RecordRsOperatorInfoChan <- param.GetOperationInfo(requestId, mode, data)
	c.SendResponse(r, nil, data, requestId)
	return
}
