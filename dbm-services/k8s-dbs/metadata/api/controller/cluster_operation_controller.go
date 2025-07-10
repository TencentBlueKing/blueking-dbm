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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	metaconst "k8s-dbs/metadata/constant"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ClusterOperationController manages metadata for cluster operation.
type ClusterOperationController struct {
	provider provider.ClusterOperationProvider
}

// NewClusterOperationController creates a new instance of ClusterOperationController.
func NewClusterOperationController(provider provider.ClusterOperationProvider) *ClusterOperationController {
	return &ClusterOperationController{provider}
}

// ListClusterOperations list cluster operations
func (c *ClusterOperationController) ListClusterOperations(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", metaconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = metaconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, metaconst.MaxFetchSize)
	pagination := commentity.Pagination{Limit: fetchSize}
	clusterOps, err := c.provider.ListClusterOperations(pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.ClusterOperationRespVo
	if err := copier.Copy(&data, clusterOps); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateClusterOperation creates a new cluster operation.
func (c *ClusterOperationController) CreateClusterOperation(ctx *gin.Context) {
	var reqVo req.ClusterOperationReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var opEntity entitys.ClusterOperationEntity
	if err := copier.Copy(&opEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.provider.CreateClusterOperation(&opEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.ClusterOperationRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
