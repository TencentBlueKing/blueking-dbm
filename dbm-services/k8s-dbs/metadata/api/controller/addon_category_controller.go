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
	"k8s-dbs/errors"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	metareqvo "k8s-dbs/metadata/vo/request"
	metarespvo "k8s-dbs/metadata/vo/response"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonCategoryController manages metadata for component operation.
type AddonCategoryController struct {
	provider provider.AddonCategoryProvider
}

// NewAddonCategoryController 构造函数
func NewAddonCategoryController(provider provider.AddonCategoryProvider) *AddonCategoryController {
	return &AddonCategoryController{provider}
}

// ListByLimit 获取 addon category 列表
func (c *AddonCategoryController) ListByLimit(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", commconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = commconst.DefaultFetchSize
	}
	fetchSize = min(fetchSize, commconst.MaxFetchSize)
	categoryTypesEntities, err := c.provider.ListByLimit(fetchSize)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []metarespvo.AddonCategoryTypesResponse
	if err := copier.Copy(&data, categoryTypesEntities); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// Create 创建 addon category
func (c *AddonCategoryController) Create(ctx *gin.Context) {
	var reqVo metareqvo.AddonCategoryRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var categoryEntity entitys.AddonCategoryEntity
	if err := copier.Copy(&categoryEntity, &reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	categoryEntity.CreatedBy = reqVo.BkUserName
	categoryEntity.UpdatedBy = reqVo.BkUserName
	added, err := c.provider.Create(&categoryEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data metarespvo.AddonCategoryResponse
	if err := copier.Copy(&data, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, &data, commconst.Success)
}
