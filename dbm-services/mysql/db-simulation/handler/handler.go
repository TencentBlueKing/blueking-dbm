/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package handler TODO
package handler

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"
)

// Response response data define
type Response struct {
	Data      interface{} `json:"data"`
	RequestID string      `json:"request_id"`
	Message   string      `json:"msg"`
	Code      int         `json:"code"`
}

// BaseHandler base handler
type BaseHandler struct {
	RequestId string
}

// SendResponse retrnurns a response
func (c *BaseHandler) SendResponse(r *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)
	r.JSON(http.StatusOK, Response{
		Code:      code,
		Message:   message,
		Data:      data,
		RequestID: c.RequestId,
	})
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
