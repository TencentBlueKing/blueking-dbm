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
	"fmt"
	"net/http"

	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
)

// BaseHandler TODO
type BaseHandler struct{}

// Response TODO
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
		c.SendResponse(r, err, nil, requestId)
		return err
	}
	if err := r.ShouldBind(&schema); err != nil {
		logger.Error("ShouldBind Failed %s", err.Error())
		c.SendResponse(r, err, nil, requestId)
		return err
	}
	logger.Info("param is %v", schema)
	return nil
}

// SendResponse retrnurns a response
func (c *BaseHandler) SendResponse(r *gin.Context, err error, data interface{}, requestId string) {
	code, message := errno.DecodeErr(err)
	r.JSON(http.StatusOK, Response{
		Code:      code,
		Message:   message,
		Data:      data,
		RequestId: requestId,
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
	}
}

// RunModuleCheck 运行模块检查
func (c BackStageHandler) RunModuleCheck(r *gin.Context) {
	task.InspectCheckResource()
	c.SendResponse(r, nil, "Check Success", "")
}

// RunAsyncCmdb TODO
func (c BackStageHandler) RunAsyncCmdb(r *gin.Context) {
	task.AsyncResourceHardInfo()
	c.SendResponse(r, nil, "async success", "")
}
