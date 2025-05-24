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
	coreconst "k8s-dbs/core/api/constants"
	"k8s-dbs/core/api/vo/resp"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// ClusterController 集群管理 Controller
type ClusterController struct {
	clusterService    *provider.ClusterProvider
	opsRequestService *provider.OpsRequestProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(clusterService *provider.ClusterProvider,
	opsRequestService *provider.OpsRequestProvider) *ClusterController {
	return &ClusterController{
		clusterService:    clusterService,
		opsRequestService: opsRequestService,
	}
}

// VerticalScaling 垂直扩缩
func (c *ClusterController) VerticalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.VerticalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.VerticalScalingSuccess)
}

// HorizontalScaling 水平扩缩
func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.HorizontalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.HorizontalScalingSuccess)
}

// StartCluster 启动集群
func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.StartClusterSuccess)
}

// RestartCluster 重启集群
func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.RestartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.RestartClusterSuccess)
}

// StopCluster 停止集群
func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StopCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.StopClusterSuccess)
}

// UpgradeCluster 升级集群
func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.UpgradeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.UpgradeClusterSuccess)
}

// UpdateCluster 更新集群
func (c *ClusterController) UpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateClusterError, err))
		return
	}
	err = c.clusterService.UpdateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.UpdateClusterSuccess)
}

// VolumeExpansion 磁盘扩容
func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	responseData, err := c.opsRequestService.VolumeExpansion(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.VolumeExpansionSuccess)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	opsRequestData, err := c.opsRequestService.DescribeOpsRequest(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	var data resp.OpsRequestDetailRespVo
	if err := copier.Copy(&data, opsRequestData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.DescribeOpsRequestSuccess)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestService.GetOpsRequestStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	var data resp.OpsRequestStatusRespVo
	if err := copier.Copy(&data, opsRequestStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.GetOpsRequestStatusSuccess)
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	err = c.clusterService.CreateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.CreateClusterSuccess)
}

// DeleteCluster 删除集群
func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	err = c.clusterService.DeleteCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.DeleteClusterSuccess)
}

// DescribeCluster 获取集群详情
func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	clusterData, err := c.clusterService.DescribeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	var data resp.ClusterDetailRespVo
	if err := copier.Copy(&data, clusterData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.DescribeClusterSuccess)
}

// GetClusterStatus 获取 cluster 状态
func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	clusterStatus, err := c.clusterService.GetClusterStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	var data resp.ClusterStatusRespVo
	if err := copier.Copy(&data, clusterStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.GetClusterStatusSuccess)
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.ExposeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.ExposeClusterSuccess)
}

// DescribeComponent 查看组件详情
func (c *ClusterController) DescribeComponent(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeComponentError, err))
		return
	}
	responseData, err := c.clusterService.DescribeComponent(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeComponentError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.DescribeComponentSuccess)
}
