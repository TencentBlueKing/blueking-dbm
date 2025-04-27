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
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ClusterController manages metadata for cluster.
type ClusterController struct {
	clusterProvider provider.K8sCrdClusterProvider
}

// NewClusterController creates a new instance of cluster.
func NewClusterController(clusterProvider provider.K8sCrdClusterProvider) *ClusterController {
	return &ClusterController{clusterProvider}
}

// GetCluster retrieves a cluster by its ID.
func (c *ClusterController) GetCluster(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cluster, err := c.clusterProvider.FindClusterByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdClusterRespVo
	if err := copier.Copy(&data, cluster); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, "OK")
}
