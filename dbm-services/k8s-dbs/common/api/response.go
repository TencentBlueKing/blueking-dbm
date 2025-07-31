/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package api

import (
	"encoding/json"
	"fmt"
	dbsErrors "k8s-dbs/errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"
)

type ResponseCode int

// Response the src response
type Response struct {
	Result  bool         `json:"result"`
	Code    ResponseCode `json:"code"`
	Data    interface{}  `json:"data"`
	Message string       `json:"message"`
	Error   interface{}  `json:"error"`
}

// SuccessResponse response after successful request execution
func SuccessResponse(ctx *gin.Context, data interface{}, message string) {
	resp := &Response{
		Result:  true,
		Code:    http.StatusOK,
		Data:    data,
		Message: message,
		Error:   nil,
	}
	ctx.JSON(http.StatusOK, resp)
	response, _ := json.Marshal(resp)
	ctx.Set("response", string(response))
}

// ErrorResponse response after failed request execution
func ErrorResponse(ctx *gin.Context, err error) {
	// 判断错误类型
	// As - 获取错误的具体实现
	var code ResponseCode
	var dbsError = new(dbsErrors.K8sDbsError)
	var message string
	if errors.As(err, &dbsError) {
		code = ResponseCode(dbsError.Code)
		message = dbsError.Message
	} else {
		code = ResponseCode(500)
		message = err.Error()
	}
	resp := &Response{
		Result:  false,
		Code:    code,
		Data:    nil,
		Message: fmt.Sprintf("%s。%s", message, dbsError.ErrorDetail),
		Error:   dbsError.ErrorDetail,
	}
	ctx.JSON(http.StatusOK, resp)
	response, _ := json.Marshal(resp)
	ctx.Set("response", string(response))
}
