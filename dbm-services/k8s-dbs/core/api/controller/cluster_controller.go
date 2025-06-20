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
	coreconst "k8s-dbs/common/api/constant"
	"k8s-dbs/core/api/vo/resp"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// ClusterController 存储集群管理 Controller
type ClusterController struct {
	clusterProvider    *provider.ClusterProvider
	opsRequestProvider *provider.OpsRequestProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(
	clusterProvider *provider.ClusterProvider,
	opsRequestProvider *provider.OpsRequestProvider,
) *ClusterController {
	return &ClusterController{
		clusterProvider:    clusterProvider,
		opsRequestProvider: opsRequestProvider,
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
	responseData, err := c.opsRequestProvider.VerticalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// HorizontalScaling 水平扩缩
func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	responseData, err := c.opsRequestProvider.HorizontalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// StartCluster 启动集群
func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.StartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// RestartCluster 重启集群
func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.RestartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// StopCluster 停止集群
func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.StopCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// UpgradeCluster 升级集群
func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.UpgradeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// UpdateCluster 更新集群
func (c *ClusterController) UpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateClusterError, err))
		return
	}
	err = c.clusterProvider.UpdateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// PartialUpdateCluster 局部更新集群
func (c *ClusterController) PartialUpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.PartialUpdateClusterError, err))
		return
	}
	err = c.clusterProvider.PartialUpdateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.PartialUpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// VolumeExpansion 磁盘扩容
func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	responseData, err := c.opsRequestProvider.VolumeExpansion(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	opsRequestData, err := c.opsRequestProvider.DescribeOpsRequest(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	var data resp.OpsRequestDetailRespVo
	if err := copier.Copy(&data, opsRequestData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestProvider.GetOpsRequestStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	var data resp.OpsRequestStatusRespVo
	if err := copier.Copy(&data, opsRequestStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	err = c.clusterProvider.CreateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// DeleteCluster 删除集群
func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	err = c.clusterProvider.DeleteCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// DescribeCluster 获取集群详情
func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	clusterData, err := c.clusterProvider.DescribeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	var data resp.ClusterDetailRespVo
	if err := copier.Copy(&data, clusterData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// GetClusterStatus 获取 cluster 状态
func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	clusterStatus, err := c.clusterProvider.GetClusterStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	var data resp.ClusterStatusRespVo
	if err := copier.Copy(&data, clusterStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.ExposeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// GetClusterEvent 查询集群事件
func (c *ClusterController) GetClusterEvent(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterEventError, err))
		return
	}
	clusterEventList, err := c.clusterProvider.GetClusterEvent(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterEventError, err))
		return
	}
	var data resp.ClusterEventRespVo
	if err := copier.Copy(&data, clusterEventList); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterEventError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}
