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
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	coreresp "k8s-dbs/core/vo/response"
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
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.VScaling,
	}
	responseData, err := c.opsRequestProvider.VerticalScaling(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VerticalScalingError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// HorizontalScaling 水平扩缩
func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.HScaling,
	}
	responseData, err := c.opsRequestProvider.HorizontalScaling(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.HorizontalScalingError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// StartCluster 启动集群
func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.StartCluster
	if request.StartList != nil {
		requestType = coreconst.StartComp
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: requestType,
	}
	responseData, err := c.opsRequestProvider.StartCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StartClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// RestartCluster 重启集群
func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.RestartCluster
	if request.RestartList != nil {
		requestType = coreconst.RestartComp
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: requestType,
	}
	responseData, err := c.opsRequestProvider.RestartCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.RestartClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// StopCluster 停止集群
func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.StopCluster
	if request.StopList != nil {
		requestType = coreconst.StopComp
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: requestType,
	}
	responseData, err := c.opsRequestProvider.StopCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.StopClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// UpgradeCluster 升级集群
func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.UpgradeComp,
	}
	responseData, err := c.opsRequestProvider.UpgradeCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// UpdateCluster 更新集群
func (c *ClusterController) UpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	if err := ctx.BindJSON(&request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.UpdateCluster,
	}
	if err := c.clusterProvider.UpdateClusterRelease(dbsContext, request, false); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateClusterError, err))

	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// PartialUpdateCluster 局部更新集群
func (c *ClusterController) PartialUpdateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.PartialUpdateCluster,
	}
	err = c.clusterProvider.UpdateClusterRelease(dbsContext, request, true)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.PartialUpdateClusterError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// VolumeExpansion 磁盘扩容
func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.VExpansion,
	}
	responseData, err := c.opsRequestProvider.VolumeExpansion(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.VolumeExpansionError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	opsRequestData, err := c.opsRequestProvider.DescribeOpsRequest(request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeOpsRequestError, err))
		return
	}
	var data coreresp.OpsRequestDetailResponse
	if err := copier.Copy(&data, opsRequestData); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestProvider.GetOpsRequestStatus(request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetOpsRequestStatusError, err))
		return
	}
	var data coreresp.OpsRequestStatusResponse
	if err := copier.Copy(&data, opsRequestStatus); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.CreateCluster,
	}
	err = c.clusterProvider.CreateCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// DeleteCluster 删除集群
func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.DeleteCluster,
	}
	err = c.clusterProvider.DeleteCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteClusterError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// DescribeCluster 获取集群详情
func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	clusterData, err := c.clusterProvider.DescribeCluster(request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeClusterError, err))
		return
	}
	var data coreresp.ClusterDetailResponse
	if err := copier.Copy(&data, clusterData); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterStatus 获取 cluster 状态
func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	clusterStatus, err := c.clusterProvider.GetClusterStatus(request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	var data coreresp.ClusterStatusResponse
	if err := copier.Copy(&data, clusterStatus); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	dbsContext := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.ExposeService,
	}
	responseData, err := c.opsRequestProvider.ExposeCluster(dbsContext, request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// GetClusterEvent 查询集群事件
func (c *ClusterController) GetClusterEvent(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	clusterEventList, err := c.clusterProvider.GetClusterEvent(request)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	var data coreresp.ClusterEventResponse
	if err := copier.Copy(&data, clusterEventList); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterService 获取集群连接信息
func (c *ClusterController) GetClusterService(ctx *gin.Context) {
	var svcEntity coreentity.K8sSvcEntity
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &svcEntity, nil); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	// 获取集群元数据
	clusterMetaEntity, err := c.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		Namespace:   svcEntity.Namespace,
		ClusterName: svcEntity.ClusterName,
	})
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	// 获取集群组件元数据
	components, err := c.getClusterComponents(clusterMetaEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	// 获取集群连接信息
	componentServices, err := c.getComponentService(components, svcEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}
	clusterService := coreresp.K8sClusterSvcResponse{
		K8sClusterName:    svcEntity.K8sClusterName,
		ClusterName:       svcEntity.ClusterName,
		Namespace:         svcEntity.Namespace,
		ComponentServices: componentServices,
	}
	api.SuccessResponse(ctx, clusterService, commconst.Success)
}

// getComponentService 获取集群组件的 service 信息
func (c *ClusterController) getComponentService(
	components []*metaentity.ClusterComponent,
	svcEntity coreentity.K8sSvcEntity,
) ([]*coreresp.K8sComponentSvcResponse, error) {
	var componentServices []*coreresp.K8sComponentSvcResponse
	for _, component := range components {
		componentSvcEntity := coreentity.K8sSvcEntity{
			K8sClusterName: svcEntity.K8sClusterName,
			Namespace:      svcEntity.Namespace,
			ComponentName:  component.Name,
			ClusterName:    svcEntity.ClusterName,
		}
		// 获取内部服务地址
		internalServices, err := c.componentProvider.GetComponentInternalSvc(&componentSvcEntity)
		if err != nil {
			return nil, err
		}

		// 获取外部服务地址
		externalServices, err := c.componentProvider.GetComponentExternalSvc(&componentSvcEntity)
		if err != nil {
			return nil, err
		}
		componentSvc := coreresp.K8sComponentSvcResponse{
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
	var clusterTopologies []*metaentity.ClusterTopology
	if err := json.Unmarshal([]byte(clusterMetaEntity.AddonInfo.Topologies), &clusterTopologies); err != nil {
		slog.Error("failed to unmarshal topologies", "topologies", clusterMetaEntity.AddonInfo.Topologies, "error", err)
		return nil, err
	}
	if len(clusterTopologies) == 0 {
		return nil, fmt.Errorf("failed to find cluster topologies")
	}
	// 获取指定 topo 的组件信息列表
	for _, topo := range clusterTopologies {
		if topo.Name == clusterMetaEntity.TopoName {
			return topo.Components, nil
		}
	}
	return nil, fmt.Errorf("failed to find cluster topologies")
}
