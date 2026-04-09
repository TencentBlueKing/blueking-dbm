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
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	coreresp "k8s-dbs/core/vo/response"
	dbserrors "k8s-dbs/errors"
	metaprovider "k8s-dbs/metadata/provider"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// OpsController 集群运维操作 Controller
// 负责集群的运维操作，包括扩缩容、启停、升级、暴露服务等
type OpsController struct {
	clusterProvider     *provider.ClusterProvider
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
	componentProvider   *provider.ComponentProvider
	opsRequestProvider  *provider.OpsRequestProvider
}

// NewOpsController 创建 OpsController 实例
func NewOpsController(
	clusterProvider *provider.ClusterProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	componentProvider *provider.ComponentProvider,
	opsRequestProvider *provider.OpsRequestProvider,
) *OpsController {
	return &OpsController{
		clusterProvider:     clusterProvider,
		clusterMetaProvider: clusterMetaProvider,
		componentProvider:   componentProvider,
		opsRequestProvider:  opsRequestProvider,
	}
}

// VerticalScaling 垂直扩缩
func (c *OpsController) VerticalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterVScaling)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  coreconst.VScaling,
	}
	responseData, err := c.opsRequestProvider.VerticalScaling(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.VerticalScalingError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// HorizontalScaling 水平扩缩
func (c *OpsController) HorizontalScaling(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterHScaling)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  coreconst.HScaling,
	}
	responseData, err := c.opsRequestProvider.HorizontalScaling(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.HorizontalScalingError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// StartCluster 启动集群
func (c *OpsController) StartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterStart)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.StartCluster
	if request.StartList != nil {
		requestType = coreconst.StartComp
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  requestType,
	}
	responseData, err := c.opsRequestProvider.StartCluster(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.StartClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// RestartCluster 重启集群
func (c *OpsController) RestartCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterRestart)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.RestartCluster
	if request.RestartList != nil {
		requestType = coreconst.RestartComp
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  requestType,
	}
	responseData, err := c.opsRequestProvider.RestartCluster(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.RestartClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// StopCluster 停止集群
func (c *OpsController) StopCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterStop)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	requestType := coreconst.StopCluster
	if request.StopList != nil {
		requestType = coreconst.StopComp
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  requestType,
	}
	responseData, err := c.opsRequestProvider.StopCluster(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.StopClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// UpgradeCluster 升级集群
func (c *OpsController) UpgradeCluster(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterUpgrade)
	if err := ctx.ShouldBindJSON(&request); err != nil {
		api.HandleValidationError(ctx, err, request)
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  coreconst.UpgradeComp,
	}
	responseData, err := c.opsRequestProvider.UpgradeCluster(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.UpgradeClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// VolumeExpansion 磁盘扩容
func (c *OpsController) VolumeExpansion(ctx *gin.Context) {
	request := &coreentity.Request{}
	c.setAPIRequestContext(ctx, request, commconst.APIClusterVExpansion)
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  coreconst.VExpansion,
	}
	responseData, err := c.opsRequestProvider.VolumeExpansion(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.VolumeExpansionError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// DescribeOpsRequest 查看 opsRequest 详情
func (c *OpsController) DescribeOpsRequest(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIOpsRequestDesc)
	request := &coreentity.Request{}
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	opsRequestData, err := c.opsRequestProvider.DescribeOpsRequest(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.DescribeOpsRequestError, err))
		return
	}
	var data coreresp.OpsRequestDetailResponse
	if err := copier.Copy(&data, opsRequestData); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetOpsRequestStatus 获取 opsRequest 状态
func (c *OpsController) GetOpsRequestStatus(ctx *gin.Context) {
	// 设置 apiName
	ctx.Set(commconst.APIName, commconst.APIOpsRequestStatus)
	request := &coreentity.Request{}
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestProvider.GetOpsRequestStatus(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.GetOpsRequestStatusError, err))
		return
	}
	var data coreresp.OpsRequestStatusResponse
	if err := copier.Copy(&data, opsRequestStatus); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.GetClusterStatusError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// ExposeCluster 暴露 cluster 服务
func (c *OpsController) ExposeCluster(ctx *gin.Context) {
	// 设置 apiName
	ctx.Set(commconst.APIName, commconst.APIClusterExpose)
	request := &coreentity.Request{}
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAdditional: &request.BKAdditional,
		RequestType:  coreconst.ExposeService,
	}
	responseData, err := c.opsRequestProvider.ExposeCluster(dbsCtx, request)
	if err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ExposeClusterError, err))
		return
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// setAPIRequestContext 设置 api 请求上下文
func (c *OpsController) setAPIRequestContext(ctx *gin.Context, request *coreentity.Request, apiName string) {
	ctx.Set(commconst.APIName, apiName)
	ctx.Set(commconst.IsClusterAPI, true)
	ctx.Set(commconst.APIRequestEntity, request)
}
