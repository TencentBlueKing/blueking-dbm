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
	coreconst "k8s-dbs/common/constant"
	commhelper "k8s-dbs/common/helper"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	respvo "k8s-dbs/core/vo/resp"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// ClusterController 存储集群管理 Controller
type ClusterController struct {
	clusterProvider     *provider.ClusterProvider
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
	componentProvider   *provider.ComponentProvider
	opsRequestProvider  *provider.OpsRequestProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(
	clusterProvider *provider.ClusterProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	componentProvider *provider.ComponentProvider,
	opsRequestProvider *provider.OpsRequestProvider,
) *ClusterController {
	return &ClusterController{
		clusterProvider:     clusterProvider,
		clusterMetaProvider: clusterMetaProvider,
		componentProvider:   componentProvider,
		opsRequestProvider:  opsRequestProvider,
	}
}

// VerticalScaling 垂直扩缩
func (c *ClusterController) VerticalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VerticalScalingError, err))
		return
	}
	responseData, err := c.opsRequestProvider.VerticalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VerticalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// HorizontalScaling 水平扩缩
func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.HorizontalScalingError, err))
		return
	}
	responseData, err := c.opsRequestProvider.HorizontalScaling(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.HorizontalScalingError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// StartCluster 启动集群
func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StartClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.StartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// RestartCluster 重启集群
func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.RestartClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.RestartCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.RestartClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// StopCluster 停止集群
func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StopClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.StopCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StopClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// UpgradeCluster 升级集群
func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.UpgradeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// UpdateCluster 更新集群
func (c *ClusterController) UpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateClusterError, err))
		return
	}
	err = c.clusterProvider.UpdateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// PartialUpdateCluster 局部更新集群
func (c *ClusterController) PartialUpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.PartialUpdateClusterError, err))
		return
	}
	err = c.clusterProvider.PartialUpdateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.PartialUpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// VolumeExpansion 磁盘扩容
func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VolumeExpansionError, err))
		return
	}
	responseData, err := c.opsRequestProvider.VolumeExpansion(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VolumeExpansionError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeOpsRequestError, err))
		return
	}
	opsRequestData, err := c.opsRequestProvider.DescribeOpsRequest(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeOpsRequestError, err))
		return
	}
	var data respvo.OpsRequestDetailRespVo
	if err := copier.Copy(&data, opsRequestData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetOpsRequestStatusError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestProvider.GetOpsRequestStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetOpsRequestStatusError, err))
		return
	}
	var data respvo.OpsRequestStatusRespVo
	if err := copier.Copy(&data, opsRequestStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	err = c.clusterProvider.CreateCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// DeleteCluster 删除集群
func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteClusterError, err))
		return
	}
	err = c.clusterProvider.DeleteCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}

// DescribeCluster 获取集群详情
func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeClusterError, err))
		return
	}
	clusterData, err := c.clusterProvider.DescribeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeClusterError, err))
		return
	}
	var data respvo.ClusterDetailRespVo
	if err := copier.Copy(&data, clusterData); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// GetClusterStatus 获取 cluster 状态
func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	clusterStatus, err := c.clusterProvider.GetClusterStatus(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	var data respvo.ClusterStatusRespVo
	if err := copier.Copy(&data, clusterStatus); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, err))
		return
	}
	responseData, err := c.opsRequestProvider.ExposeCluster(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// GetClusterEvent 查询集群事件
func (c *ClusterController) GetClusterEvent(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	clusterEventList, err := c.clusterProvider.GetClusterEvent(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	var data respvo.ClusterEventRespVo
	if err := copier.Copy(&data, clusterEventList); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, coreconst.Success)
}

// GetClusterService 获取集群连接信息
func (c *ClusterController) GetClusterService(ctx *gin.Context) {
	var svcEntity coreentity.K8sSvcEntity
	if err := commhelper.DecodeParams(ctx, commhelper.BuildParams, &svcEntity, nil); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	clusterParams := &metaentity.ClusterQueryParams{
		Namespace:   svcEntity.Namespace,
		ClusterName: svcEntity.ClusterName,
	}
	clusterMetaEntity, err := c.clusterMetaProvider.FindByParams(clusterParams)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	// 获取集群组件列表
	components, err := c.getClusterComponents(clusterMetaEntity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	// 获取集群连接信息
	componentServices, err := c.getComponentService(components, svcEntity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	clusterService := respvo.K8sClusterSvcRespVo{
		K8sClusterName:    svcEntity.K8sClusterName,
		ClusterName:       svcEntity.ClusterName,
		Namespace:         svcEntity.Namespace,
		ComponentServices: componentServices,
	}
	coreentity.SuccessResponse(ctx, clusterService, coreconst.Success)
}

// getComponentService 获取集群组件的 service 信息
func (c *ClusterController) getComponentService(
	components []*metaentity.ClusterComponent,
	svcEntity coreentity.K8sSvcEntity,
) ([]*respvo.K8sComponentSvcRespVo, error) {
	var componentServices []*respvo.K8sComponentSvcRespVo
	for _, component := range components {
		componentSvcEntity := coreentity.K8sSvcEntity{
			K8sClusterName: svcEntity.K8sClusterName,
			Namespace:      svcEntity.Namespace,
			ComponentName:  component.Name,
			ClusterName:    svcEntity.ClusterName,
		}
		internalServices, err := c.componentProvider.GetComponentInternalSvc(&componentSvcEntity)
		if err != nil {
			return nil, err
		}
		externalServices, err := c.componentProvider.GetComponentExternalSvc(&componentSvcEntity)
		if err != nil {
			return nil, err
		}
		componentSvc := respvo.K8sComponentSvcRespVo{
			K8sClusterName:      componentSvcEntity.K8sClusterName,
			ClusterName:         componentSvcEntity.ClusterName,
			Namespace:           componentSvcEntity.Namespace,
			ComponentName:       componentSvcEntity.ComponentName,
			InternalServiceInfo: internalServices,
			ExternalServiceInfo: externalServices,
		}
		componentServices = append(componentServices, &componentSvc)
	}
	return componentServices, nil
}

// getClusterComponents 获取集群组件列表（只是组件名称不是组件实例名）
func (c *ClusterController) getClusterComponents(clusterMetaEntity *metaentity.K8sCrdClusterEntity) (
	[]*metaentity.ClusterComponent,
	error,
) {
	topologiesStr := clusterMetaEntity.AddonInfo.Topologies
	var clusterTopologies []*metaentity.ClusterTopology
	if err := json.Unmarshal([]byte(topologiesStr), &clusterTopologies); err != nil {
		slog.Error("failed to unmarshal topologies", "topologies", topologiesStr, "error", err)
		return nil, err
	}
	if clusterTopologies == nil {
		return nil, fmt.Errorf("failed to find cluster topologies")
	}
	var components []*metaentity.ClusterComponent
	for _, topo := range clusterTopologies {
		if topo.Name == clusterMetaEntity.TopoName {
			components = topo.Components
			break
		}
	}
	return components, nil
}
