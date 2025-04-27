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
	types "k8s-dbs/core/api/constants"
	entity2 "k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider/clustermanage"
	"k8s-dbs/core/provider/opsmanage"

	"github.com/gin-gonic/gin"
)

// ClusterController 集群管理 Controller
type ClusterController struct {
	clusterService    *clustermanage.ClusterProvider
	opsRequestService *opsmanage.OpsRequestProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(clusterService *clustermanage.ClusterProvider,
	opsRequestService *opsmanage.OpsRequestProvider) *ClusterController {
	return &ClusterController{
		clusterService:    clusterService,
		opsRequestService: opsRequestService,
	}
}

// VerticalScaling 垂直扩缩
func (c *ClusterController) VerticalScaling(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.VerticalScaling(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.VerticalScalingSuccess)
}

// HorizontalScaling 水平扩缩
func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.HorizontalScaling(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.HorizontalScalingSuccess)
}

// StartCluster 启动集群
func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StartCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.StartClusterSuccess)
}

// RestartCluster 重启集群
func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.RestartCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.RestartClusterSuccess)
}

// StopCluster 停止集群
func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StopCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.StopClusterSuccess)
}

// UpgradeCluster 升级集群
func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.UpgradeCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.UpgradeClusterSuccess)
}

// VolumeExpansion 磁盘扩容
func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	responseData, err := c.opsRequestService.VolumeExpansion(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.VolumeExpansionSuccess)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	opsRequestData, err := c.opsRequestService.DescribeOpsRequest(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	entity2.SuccessResponse(ctx, opsRequestData, types.DescribeOpsRequestSuccess)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestService.GetOpsRequestStatus(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	entity2.SuccessResponse(ctx, opsRequestStatus, types.GetOpsRequestStatusSuccess)
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	err = c.clusterService.CreateCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, nil, types.CreateClusterSuccess)
}

// DeleteCluster 删除集群
func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	err = c.clusterService.DeleteCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, nil, types.DeleteClusterSuccess)
}

// DescribeCluster 获取集群详情
func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	clusterData, err := c.clusterService.DescribeCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, clusterData, types.DescribeClusterSuccess)
}

// GetClusterStatus 获取 cluster 状态
func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	clusterStatus, err := c.clusterService.GetClusterStatus(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	entity2.SuccessResponse(ctx, clusterStatus, types.GetClusterStatsuSuccess)
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &entity2.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.ExposeCluster(request)
	if err != nil {
		entity2.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	entity2.SuccessResponse(ctx, responseData, types.ExposeClusterSuccess)
}
