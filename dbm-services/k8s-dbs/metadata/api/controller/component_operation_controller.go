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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/errors"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/request"
	"k8s-dbs/metadata/vo/response"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ComponentOperationController manages metadata for component operation.
type ComponentOperationController struct {
	provider provider.ComponentOperationProvider
}

// NewComponentOperationController creates a new instance of ComponentOperationController.
func NewComponentOperationController(provider provider.ComponentOperationProvider) *ComponentOperationController {
	return &ComponentOperationController{provider}
}

// ListComponentOperations list component operations
func (c *ComponentOperationController) ListComponentOperations(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", commconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = commconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, commconst.MaxFetchSize)
	pagination := commentity.Pagination{Limit: fetchSize}
	clusterOps, err := c.provider.ListComponentOperations(pagination)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []response.ComponentOperationResponse
	if err = copier.Copy(&data, clusterOps); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// CreateComponentOperation creates a new component operation.
func (c *ComponentOperationController) CreateComponentOperation(ctx *gin.Context) {
	var reqVo request.ComponentOperationRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var opEntity entitys.ComponentOperationEntity
	if err := copier.Copy(&opEntity, &reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	added, err := c.provider.CreateComponentOperation(&opEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data response.ComponentOperationResponse
	if err = copier.Copy(&data, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}
