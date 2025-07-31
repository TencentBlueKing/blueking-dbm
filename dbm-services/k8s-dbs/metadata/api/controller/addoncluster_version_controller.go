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

// AddonClusterVersionController manages metadata for addons.
type AddonClusterVersionController struct {
	acVersionProvider provider.AddonClusterVersionProvider
}

// NewAddonClusterVersionController creates a new instance of AddonClusterVersionController.
func NewAddonClusterVersionController(
	acVersionProvider provider.AddonClusterVersionProvider,
) *AddonClusterVersionController {
	return &AddonClusterVersionController{acVersionProvider}
}

// ListAcVersions 获取 addon cluster version 列表
func (a *AddonClusterVersionController) ListAcVersions(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", commconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = commconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, commconst.MaxFetchSize)
	pagination := commentity.Pagination{Limit: fetchSize}
	acVersions, err := a.acVersionProvider.ListAcVersion(pagination)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []response.AddonClusterVersionResponse
	if err := copier.Copy(&data, acVersions); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetAcVersion 根据 ID 查找 addon cluster version
func (a *AddonClusterVersionController) GetAcVersion(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	addon, err := a.acVersionProvider.FindAcVersionByID(id)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data response.AddonClusterVersionResponse
	if err := copier.Copy(&data, addon); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// CreateAcVersion 创建 addon cluster version
func (a *AddonClusterVersionController) CreateAcVersion(ctx *gin.Context) {
	var acVersionVo request.AddonClusterVersionRequest
	if err := ctx.ShouldBindJSON(&acVersionVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var acVersionEntity entitys.AddonClusterVersionEntity
	if err := copier.Copy(&acVersionEntity, &acVersionVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	added, err := a.acVersionProvider.CreateAcVersion(&acVersionEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data response.AddonClusterVersionResponse
	if err := copier.Copy(&data, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateAcVersion 更新 addon cluster version.
func (a *AddonClusterVersionController) UpdateAcVersion(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var acVersionVo request.AddonClusterVersionRequest
	if err := ctx.ShouldBindJSON(&acVersionVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var acVersionEntity entitys.AddonClusterVersionEntity
	if err := copier.Copy(&acVersionEntity, acVersionVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	acVersionEntity.ID = id
	rows, err := a.acVersionProvider.UpdateAcVersion(&acVersionEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteAcVersion 删除 addon cluster version.
func (a *AddonClusterVersionController) DeleteAcVersion(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	rows, err := a.acVersionProvider.DeleteAcVersionByID(id)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
