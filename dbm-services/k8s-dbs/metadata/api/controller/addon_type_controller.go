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
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonTypeController manages metadata for component operation.
type AddonTypeController struct {
	provider provider.AddonTypeProvider
}

// NewAddonTypeController creates a new instance of AddonTypeController.
func NewAddonTypeController(provider provider.AddonTypeProvider) *AddonTypeController {
	return &AddonTypeController{provider}
}

// ListByLimit 获取 addon type 列表
func (a *AddonTypeController) ListByLimit(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", commconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = commconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, commconst.MaxFetchSize)
	addonTypeEntities, err := a.provider.ListByLimit(fetchSize)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.AddonTypeResp
	if err := copier.Copy(&data, addonTypeEntities); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// Create 创建 addon type
func (a *AddonTypeController) Create(ctx *gin.Context) {
	var reqVo req.AddonTypeReq
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var addonTypeEntity entitys.AddonTypeEntity
	if err := copier.Copy(&addonTypeEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	addonTypeEntity.CreatedBy = reqVo.BkUserName
	addonTypeEntity.UpdatedBy = reqVo.BkUserName
	added, err := a.provider.Create(&addonTypeEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.AddonTypeResp
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
