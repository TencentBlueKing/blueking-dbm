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
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/request"
	"k8s-dbs/metadata/vo/response"
	"strconv"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// AddonTopologyController manages metadata for component operation.
type AddonTopologyController struct {
	provider provider.AddonTopologyProvider
}

// NewAddonTopologyController 构造函数
func NewAddonTopologyController(provider provider.AddonTopologyProvider) *AddonTopologyController {
	return &AddonTopologyController{provider}
}

// Create 创建 addon topology
func (a *AddonTopologyController) Create(ctx *gin.Context) {
	var reqVo request.AddonTopologyRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var topoEntity metaenitty.AddonTopologyEntity
	if err := copier.Copy(&topoEntity, &reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	topoEntity.CreatedBy = reqVo.BkUserName
	topoEntity.UpdatedBy = reqVo.BkUserName
	added, err := a.provider.Create(&topoEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data response.AddonTopologyResponse
	if err := copier.Copy(&data, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetByID 按照 id 检索 addon topology
func (a *AddonTopologyController) GetByID(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	repo, err := a.provider.FindByID(id)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data response.AddonTopologyResponse
	if err := copier.Copy(&data, repo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetByParams 按照参数检索 addon topology
func (a *AddonTopologyController) GetByParams(ctx *gin.Context) {
	var topoQueryParams metaenitty.AddonTopologyQueryParams
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &topoQueryParams, nil); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	topoEntities, err := a.provider.FindByParams(&topoQueryParams)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
	}
	var data []response.AddonTopologyResponse
	if err := copier.Copy(&data, topoEntities); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}
