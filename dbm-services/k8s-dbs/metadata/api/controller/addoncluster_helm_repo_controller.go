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
	"k8s-dbs/core/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ClusterHelmRepoController manages metadata for cluster helm repo.
type ClusterHelmRepoController struct {
	clusterHelmRepoProvider provider.AddonClusterHelmRepoProvider
}

// NewClusterHelmRepoController creates a new instance of cluster helm repo..
func NewClusterHelmRepoController(
	clusterHelmRepoProvider provider.AddonClusterHelmRepoProvider,
) *ClusterHelmRepoController {
	return &ClusterHelmRepoController{clusterHelmRepoProvider}
}

// GetClusterHelmRepoByID retrieves a cluster helm repo by its ID.
func (c *ClusterHelmRepoController) GetClusterHelmRepoByID(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	repo, err := c.clusterHelmRepoProvider.FindHelmRepoByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.AddonClusterHelmRepoRespVo
	if err := copier.Copy(&data, repo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateClusterHelmRepo create cluster helm repo
func (c *ClusterHelmRepoController) CreateClusterHelmRepo(ctx *gin.Context) {
	var reqVo req.AddonClusterHelmRepoRespVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var repoEntity metaentity.AddonClusterHelmRepoEntity
	if err := copier.Copy(&repoEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &reqVo.BKAuth,
	}
	addedRepo, err := c.clusterHelmRepoProvider.CreateHelmRepo(&dbsContext, &repoEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.AddonClusterHelmRepoRespVo
	if err := copier.Copy(&data, addedRepo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterHelmRepoByParam get addon cluster helm repo by its Param.
func (c *ClusterHelmRepoController) GetClusterHelmRepoByParam(ctx *gin.Context) {
	chartName := ctx.Param("chartName")
	chartVersion := ctx.Param("chartVersion")
	if chartName == "" || chartVersion == "" {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr,
			fmt.Errorf("chartName 或 chartVersion 参数不能为空")))
		return
	}

	params := &metaentity.HelmRepoQueryParams{
		ChartName:    chartName,
		ChartVersion: chartVersion,
	}

	repo, err := c.clusterHelmRepoProvider.FindByParams(params)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var respVo resp.AddonClusterHelmRepoRespVo
	if err = copier.Copy(&respVo, repo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}
