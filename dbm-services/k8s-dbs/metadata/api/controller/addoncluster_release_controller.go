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
	coreentity "k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/response"
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
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	cluster, err := c.clusterReleaseProvider.FindClusterReleaseByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data response.AddonClusterReleaseResponse
	if err := copier.Copy(&data, cluster); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterReleaseByParam get addon cluster release by its Param.
func (c *ClusterReleaseController) GetClusterReleaseByParam(ctx *gin.Context) {
	releaseName := ctx.Param("releaseName")
	namespace := ctx.Param("namespace")
	if releaseName == "" || namespace == "" {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, fmt.Errorf("cluster_name 参数不能为空")))
		return
	}
	params := &metaentity.ClusterReleaseQueryParams{
		ReleaseName: releaseName,
		Namespace:   namespace,
	}
	clusterRelease, err := c.clusterReleaseProvider.FindByParams(params)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var respVo response.AddonClusterReleaseResponse
	if err = copier.Copy(&respVo, clusterRelease); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var chartValues map[string]interface{}
	if err = json.Unmarshal([]byte(clusterRelease.ChartValues), &chartValues); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	respVo.ChartValues = chartValues
	coreentity.SuccessResponse(ctx, respVo, commconst.Success)
}
