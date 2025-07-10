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
	"fmt"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonHelmRepoController manages metadata for addon helm repo.
type AddonHelmRepoController struct {
	addonHelmRepoProvider provider.AddonHelmRepoProvider
}

// NewAddonHelmRepoController creates a new instance of addon helm repo.
func NewAddonHelmRepoController(
	addonHelmRepoProvider provider.AddonHelmRepoProvider,
) *AddonHelmRepoController {
	return &AddonHelmRepoController{addonHelmRepoProvider}
}

// GetAddonHelmRepoByID retrieves a addon helm repo by its ID.
func (c *AddonHelmRepoController) GetAddonHelmRepoByID(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	repo, err := c.addonHelmRepoProvider.FindHelmRepoByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.AddonHelmRepoRespVo
	if err := copier.Copy(&data, repo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateAddonHelmRepo create addon helm repo
func (c *AddonHelmRepoController) CreateAddonHelmRepo(ctx *gin.Context) {
	var reqVo req.AddonHelmRepoRespVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var repoEntity metaentity.AddonHelmRepoEntity
	if err := copier.Copy(&repoEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &reqVo.BKAuth,
	}
	addedRepo, err := c.addonHelmRepoProvider.CreateHelmRepo(&dbsContext, &repoEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.AddonHelmRepoRespVo
	if err := copier.Copy(&data, addedRepo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// GetAddonHelmRepoByParam get addon helm repo by its Param.
func (c *AddonHelmRepoController) GetAddonHelmRepoByParam(ctx *gin.Context) {
	chartName := ctx.Param("chartName")
	chartVersion := ctx.Param("chartVersion")
	if chartName == "" || chartVersion == "" {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr,
			fmt.Errorf("chartName 或 chartVersion 参数不能为空")))
		return
	}
	params := &metaentity.HelmRepoQueryParams{
		ChartName:    chartName,
		ChartVersion: chartVersion,
	}
	repo, err := c.addonHelmRepoProvider.FindByParams(params)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var respVo resp.AddonHelmRepoRespVo
	if err = copier.Copy(&respVo, repo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}
