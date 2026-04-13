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
	commvalidator "k8s-dbs/common/validator"
	dbserrors "k8s-dbs/errors"
	infresp "k8s-dbs/infrastructure/response"
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
	if b, err := json.Marshal(resp); err == nil {
		ctx.Set("response", string(b))
	}
}

// ErrorResponse response after failed request execution
func ErrorResponse(ctx *gin.Context, err error) {
	var code ResponseCode
	var dbsError = new(dbserrors.K8sDbsError)
	var message string
	var errorDetail string
	if errors.As(err, &dbsError) {
		code = ResponseCode(dbsError.Code)
		message = dbsError.Message
		errorDetail = dbsError.ErrorDetail
	} else {
		code = ResponseCode(500)
		message = err.Error()
		errorDetail = ""
	}

	var displayMessage string
	if errorDetail != "" {
		displayMessage = fmt.Sprintf("%s。%s", message, errorDetail)
	} else {
		displayMessage = message
	}

	resp := &Response{
		Result:  false,
		Code:    code,
		Data:    nil,
		Message: displayMessage,
		Error:   errorDetail,
	}
	ctx.JSON(http.StatusOK, resp)
	if b, marshalErr := json.Marshal(resp); marshalErr == nil {
		ctx.Set("response", string(b))
	}
}

// PermissionDeniedResponseBody 无权限响应结构，与 DBM 返回格式对齐
type PermissionDeniedResponseBody struct {
	Result  bool                `json:"result"`
	Code    dbserrors.ErrorCode `json:"code"`
	Data    *infresp.ApplyData  `json:"data"`
	Message string              `json:"message"`
}

// PermissionDeniedResponse 返回无权限响应，附带权限申请数据和 URL。
// 完整的 permission + apply_url 数据并触发权限申请弹窗。
func PermissionDeniedResponse(ctx *gin.Context, applyData *infresp.ApplyData) {
	resp := &PermissionDeniedResponseBody{
		Result:  false,
		Code:    dbserrors.OperationForbidden,
		Data:    applyData,
		Message: "禁止执行该操作(您没有当前操作的权限)",
	}

	ctx.JSON(http.StatusOK, resp)
	if b, err := json.Marshal(resp); err == nil {
		ctx.Set("response", string(b))
	}
}

// HandleValidationError 封装校验错误处理逻辑
func HandleValidationError(ctx *gin.Context, err error, request any) {
	ok, msg := commvalidator.ValidateError(err, request)
	if ok {
		ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, errors.New(msg)))
	} else {
		ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
	}
}
