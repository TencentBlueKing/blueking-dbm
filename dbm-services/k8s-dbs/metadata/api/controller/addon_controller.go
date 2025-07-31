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
	coreentity "k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	metareq "k8s-dbs/metadata/vo/request"
	metaresp "k8s-dbs/metadata/vo/response"
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
	sizeStr := ctx.DefaultQuery("size", commconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = commconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, commconst.MaxFetchSize)
	pagination := commentity.Pagination{Limit: fetchSize}
	addons, err := a.addonProvider.ListStorageAddons(pagination)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []metaresp.AddonResponse
	if err := copier.Copy(&data, addons); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// GetAddon retrieves an addon by its ID.
func (a *AddonController) GetAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	addon, err := a.addonProvider.FindStorageAddonByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data metaresp.AddonResponse
	if err := copier.Copy(&data, addon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// GetVersions 获取组件版本
func (a *AddonController) GetVersions(ctx *gin.Context) {
	var paramsReq metareq.AddonVersionRequest
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &paramsReq, nil); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var paramsEntity metaentity.AddonVersionQueryParams
	if err := copier.Copy(&paramsEntity, &paramsReq); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	versionEntities, err := a.addonProvider.FindVersionsByParams(&paramsEntity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []*metaresp.AddonVersionResp
	if err := copier.Copy(&data, versionEntities); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateAddon creates a new addon.
func (a *AddonController) CreateAddon(ctx *gin.Context) {
	var addon metareq.AddonRequest
	if err := ctx.ShouldBindJSON(&addon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var addonEntity metaentity.K8sCrdStorageAddonEntity
	if err := copier.Copy(&addonEntity, &addon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &addon.BKAuth,
	}
	addedAddon, err := a.addonProvider.CreateStorageAddon(&dbsContext, &addonEntity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data metaresp.AddonResponse
	if err := copier.Copy(&data, addedAddon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateAddon updates an existing addon.
func (a *AddonController) UpdateAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var addon metareq.AddonRequest
	if err := ctx.ShouldBindJSON(&addon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var addonEntity metaentity.K8sCrdStorageAddonEntity
	if err := copier.Copy(&addonEntity, addon); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &addon.BKAuth,
	}
	addonEntity.ID = id
	rows, err := a.addonProvider.UpdateStorageAddon(&dbsContext, &addonEntity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteAddon deletes an addon by its ID.
func (a *AddonController) DeleteAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	rows, err := a.addonProvider.DeleteStorageAddonByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
