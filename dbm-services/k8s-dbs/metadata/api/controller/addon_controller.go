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
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/req"
	"k8s-dbs/metadata/api/vo/resp"
	metaconst "k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/provider"
	entitys "k8s-dbs/metadata/provider/entity"
	"k8s-dbs/metadata/utils"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonController manages metadata for addons.
type AddonController struct {
	addonProvider provider.K8sCrdStorageAddonProvider
}

// NewAddonController creates a new instance of AddonController.
func NewAddonController(addonProvider provider.K8sCrdStorageAddonProvider) *AddonController {
	return &AddonController{addonProvider}
}

// ListAddons 获取当前系统支持的 addon 列表
func (a *AddonController) ListAddons(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", metaconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = metaconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, metaconst.MaxFetchSize)
	pagination := utils.Pagination{Limit: fetchSize}
	addons, err := a.addonProvider.ListStorageAddons(pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.K8sCrdAddonRespVo
	if err := copier.Copy(&data, addons); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, "OK")
}

// GetAddon retrieves an addon by its ID.
func (a *AddonController) GetAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	addon, err := a.addonProvider.FindStorageAddonByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdAddonRespVo
	if err := copier.Copy(&data, addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, "OK")
}

// CreateAddon creates a new addon.
func (a *AddonController) CreateAddon(ctx *gin.Context) {
	var addon req.K8sCrdAddonReqVo
	if err := ctx.ShouldBindJSON(&addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var addonEntity entitys.K8sCrdStorageAddonEntity
	if err := copier.Copy(&addonEntity, &addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	addedAddon, err := a.addonProvider.CreateStorageAddon(&addonEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdAddonRespVo
	if err := copier.Copy(&data, addedAddon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, "OK")
}

// UpdateAddon updates an existing addon.
func (a *AddonController) UpdateAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var addon req.K8sCrdAddonReqVo
	if err := ctx.ShouldBindJSON(&addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var addonEntity entitys.K8sCrdStorageAddonEntity
	if err := copier.Copy(&addonEntity, addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	addonEntity.ID = id
	rows, err := a.addonProvider.UpdateStorageAddon(&addonEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
}

// DeleteAddon deletes an addon by its ID.
func (a *AddonController) DeleteAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	rows, err := a.addonProvider.DeleteStorageAddonByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
}
