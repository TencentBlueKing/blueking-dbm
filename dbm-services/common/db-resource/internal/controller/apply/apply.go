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
	"dbm-services/common/db-resource/internal/middleware"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
)

func init() {
	middleware.RequestLoggerFilter.Add("/resource/apply")
	middleware.RequestLoggerFilter.Add("/resource/pre-apply")
	middleware.RequestLoggerFilter.Add("/resource/confirm/apply")
}

// ApplyHandler TODO
// nolint
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

// ConfirmApplyParam 配合预申请资源接口，确认占用资源
type ConfirmApplyParam struct {
	RequestId string `json:"request_id" binding:"required"`
	HostIds   []int  `json:"host_ids" binding:"gt=0,dive,required" `
}

// ConfirmApply 确认占用资源
func (c *ApplyHandler) ConfirmApply(r *gin.Context) {
	var param ConfirmApplyParam
	if c.Prepare(r, &param) != nil {
		return
	}
	hostIds := lo.Uniq(param.HostIds)
	var cnt int64
	err := model.DB.Self.Table(model.TbRpApplyDetailLogName()).Where("request_id = ?", param.RequestId).Count(&cnt).Error
	if err != nil {
		logger.Error("use request id %s,query apply resouece failed %s", param.RequestId, err.Error())
		return
	}
	if len(hostIds) != int(cnt) {
		c.SendResponse(r, fmt.Errorf("need return resource count is %d,but use request id only found total count %d",
			len(hostIds), cnt), "")
		return
	}
	var rs []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id in (?) and status != ? ", hostIds,
		model.Prepoccupied).Find(&rs).Error
	if err != nil {
		c.SendResponse(r, err, err.Error())
		return
	}
	if len(rs) > 0 {
		c.SendResponse(r, fmt.Errorf("the following example:%s,abnormal state", buildErrMsg(rs)), "")
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
		c.SendResponse(r, err, err.Error())
		return
	}
	uerr := model.DB.Self.Table(model.TbRpOperationInfoTableName()).Where("request_id = ?",
		param.RequestId).Update("status", model.Used).Error
	if uerr != nil {
		logger.Warn("update tb_rp_operation_info failed %s ", uerr.Error())
	}
	archive(hostIds)
	c.SendResponse(r, nil, "successful")
}

func buildErrMsg(abnormalRsList []model.TbRpDetail) string {
	var errMsg string
	for _, v := range abnormalRsList {
		errMsg += fmt.Sprintf("%s:%s\n", v.IP, v.Status)
	}
	return errMsg
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

// ApplyResource apply resource
func (c *ApplyHandler) ApplyResource(r *gin.Context) {
	c.ApplyBase(r, model.Used)
}

// PreApplyResource pre apply resource
func (c *ApplyHandler) PreApplyResource(r *gin.Context) {
	c.ApplyBase(r, model.Prepoccupied)
}

func newLocker(key string, requestId string) *lock.SpinLock {
	return lock.NewSpinLock(&lock.RedisLock{Name: key, RandKey: requestId, Expiry: 120 * time.Second}, 60,
		350*time.Millisecond)
}

// ApplyBase apply resource base func
func (c *ApplyHandler) ApplyBase(r *gin.Context, mode string) {
	task.RuningTask <- struct{}{}
	defer func() { <-task.RuningTask }()
	logger.Info("start apply resource ... ")
	var param apply.RequestInputParam
	var pickers []*apply.PickerObject
	var err error
	if c.Prepare(r, &param) != nil {
		return
	}
	if err = param.ParamCheck(); err != nil {
		c.SendResponse(r, errno.ErrApplyResourceParamCheck.AddErr(err), err.Error())
		return
	}
	// get the resource lock if it is dry run you do not need to acquire it
	if !param.DryRun {
		lock := newLocker(param.LockKey(), c.RequestId)
		if err = lock.Lock(); err != nil {
			c.SendResponse(r, errno.ErrResourceLock.AddErr(err), err.Error())
			return
		}
		defer func() {
			if err = lock.Unlock(); err != nil {
				logger.Error(fmt.Sprintf("unlock failed %s", err.Error()))
				return
			}
		}()
	}
	defer func() {
		if err != nil {
			apply.RollBackAllInstanceUnused(pickers)
		}
	}()
	pickers, err = apply.CycleApply(param)
	if err != nil {
		c.SendResponse(r, errno.ErrResourceinsufficient.Add(param.BuildMessage()+"\n"+err.Error()), "")
		return
	}
	if param.DryRun {
		c.SendResponse(r, nil, map[string]interface{}{"check_success": true})
		return
	}
	data, err := apply.LockReturnPickers(pickers, mode)
	if err != nil {
		c.SendResponse(r, errno.ErresourceLockReturn.AddErr(err), nil)
		return
	}
	logger.Info(fmt.Sprintf("The %s, will return %d machines", c.RequestId, len(data)))
	task.ApplyResponeLogChan <- task.ApplyResponeLogItem{
		RequestId: c.RequestId,
		Data:      data,
	}
	task.RecordRsOperatorInfoChan <- param.GetOperationInfo(c.RequestId, mode, data)
	c.SendResponse(r, nil, data)
}
