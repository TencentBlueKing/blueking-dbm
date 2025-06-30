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
	"encoding/json"
	"fmt"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ClusterReleaseController manages metadata for cluster release.
type ClusterReleaseController struct {
	clusterReleaseProvider provider.AddonClusterReleaseProvider
}

// NewClusterReleaseController creates a new instance of addon cluster release.
func NewClusterReleaseController(
	clusterReleaseProvider provider.AddonClusterReleaseProvider,
) *ClusterReleaseController {
	return &ClusterReleaseController{clusterReleaseProvider}
}

// GetClusterRelease retrieves a cluster release by its ID.
func (c *ClusterReleaseController) GetClusterRelease(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cluster, err := c.clusterReleaseProvider.FindClusterReleaseByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdClusterRespVo
	if err := copier.Copy(&data, cluster); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterReleaseByParam get addon cluster release by its Param.
func (c *ClusterReleaseController) GetClusterReleaseByParam(ctx *gin.Context) {
	releaseNameParam := ctx.Param("releaseName")
	namespaceParam := ctx.Param("namespace")
	if releaseNameParam == "" || namespaceParam == "" {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, fmt.Errorf("cluster_name 参数不能为空")))
		return
	}
	paramsRelease := map[string]interface{}{
		"release_name": releaseNameParam,
		"namespace":    namespaceParam,
	}
	clusterRelease, err := c.clusterReleaseProvider.FindByParams(paramsRelease)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var respVo resp.AddonClusterReleaseRespVo
	if err = copier.Copy(&respVo, clusterRelease); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	// Deserialization
	var chartValues map[string]interface{}
	if err = json.Unmarshal([]byte(clusterRelease.ChartValues), &chartValues); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	respVo.ChartValues = chartValues
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}
