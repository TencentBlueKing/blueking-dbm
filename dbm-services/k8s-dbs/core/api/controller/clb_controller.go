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

package controller

import (
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	dbserrors "k8s-dbs/errors"
	infreq "k8s-dbs/infrastructure/request"
	"k8s-dbs/infrastructure/thirdapi"

	"github.com/gin-gonic/gin"
)

// ClbController CLB 管理 Controller
type ClbController struct {
	clbService *thirdapi.ClbAPIService
}

// NewClbController 创建 ClbController 实例
func NewClbController(clbService *thirdapi.ClbAPIService) *ClbController {
	return &ClbController{
		clbService: clbService,
	}
}

// CreateClb 创建 CLB
func (c *ClbController) CreateClb(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIClbCreate)
	request := &infreq.CreateClbRequest{}
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	clbID, err := c.clbService.CreateClb(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.CreateClbError, err))
		return
	}
	api.SuccessResponse(ctx, clbID, commconst.Success)
}

// GetClb 获取 CLB 信息
func (c *ClbController) GetClb(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIClbGet)
	request := &infreq.GetClbRequest{}
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	clbResp, err := c.clbService.GetClb(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.GetClbError, err))
		return
	}
	api.SuccessResponse(ctx, clbResp.Data, commconst.Success)
}
