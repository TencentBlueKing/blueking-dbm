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
	"fmt"
	coreentity "k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	webconfig "k8s-dbs/dataweb/api/config"
	webreq "k8s-dbs/dataweb/vo/request"
	"k8s-dbs/dataweb/vo/response"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	metaresponse "k8s-dbs/metadata/vo/response"
	"strconv"
	"time"

	"github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// ClusterController 存储集群管理 Controller
type ClusterController struct {
	clusterProvider     *provider.ClusterProvider
	opsRequestProvider  *provider.OpsRequestProvider
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
	opsProvider         metaprovider.K8sCrdOpsRequestProvider
	componentProvider   *provider.ComponentProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(
	clusterProvider *provider.ClusterProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	opsProvider metaprovider.K8sCrdOpsRequestProvider,
	opsRequestProvider *provider.OpsRequestProvider,
	componentProvider *provider.ComponentProvider,
) *ClusterController {
	return &ClusterController{
		clusterProvider:     clusterProvider,
		clusterMetaProvider: clusterMetaProvider,
		opsProvider:         opsProvider,
		opsRequestProvider:  opsRequestProvider,
		componentProvider:   componentProvider,
	}
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &webreq.ClusterInstallRequest{}
	if err := ctx.ShouldBindJSON(request); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	clusterConfig, err := webconfig.ClusterConfBuilderFactory.
		GetBuilder(coreconst.StorageAddonType(request.BasicInfo.StorageAddonType)).
		BuildConfig(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	dbsCtx := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.CreateCluster,
	}
	if err := c.clusterProvider.CreateCluster(dbsCtx, clusterConfig); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, commconst.Success)
}

// GetClusterList 获取集群列表
func (c *ClusterController) GetClusterList(ctx *gin.Context) {
	pagination, err := commutil.BuildPagination(ctx)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterError, err))
		return
	}
	requestParams, err := commutil.BuildClusterListParams(ctx)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterTypeError, err))
		return
	}
	clusters, count, err := c.clusterMetaProvider.ListClusters(requestParams, pagination)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []response.ClusterResponse
	if err := copier.Copy(&data, clusters); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}

	for idx, clusterEntity := range data {
		data[idx].BkBizTitle = fmt.Sprintf("[%d]%s", clusterEntity.BkBizID, clusterEntity.BkBizName)
		data[idx].TopoNameAlias = getTopoNameAlias(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
		c.processingClusterOpsStatus(ctx, &data[idx])
	}

	var responseData = metaresponse.PageResult{
		Count:  count,
		Result: data,
	}
	coreentity.SuccessResponse(ctx, responseData, commconst.Success)
}

// GetClusterInfo 获取集群详情
func (c *ClusterController) GetClusterInfo(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	cluster, err := c.clusterMetaProvider.FindClusterByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data response.ClusterResponse
	if err := copier.Copy(&data, cluster); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	data.BkBizTitle = fmt.Sprintf("[%d]%s", data.BkBizID, data.BkBizName)
	data.TopoNameAlias = getTopoNameAlias(data.AddonInfo.AddonType, data.TopoName)
	c.processingClusterOpsStatus(ctx, &data)
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// getTopoNameAlias 获取 topo 别名
func getTopoNameAlias(addonType, topoName string) string {
	if innerMap, ok := topoNameAliasMapping[addonType]; ok {
		if alias, ok := innerMap[topoName]; ok {
			return alias
		}
	}
	return ""
}

var topoNameAliasMapping = map[string]map[string]string{
	"victoriametrics": {
		"cluster": "全套服务",
		"select":  "查询服务",
	},
}

// processingClusterOpsStatus 处理集群操作状态
func (c *ClusterController) processingClusterOpsStatus(ctx *gin.Context, data *response.ClusterResponse) {
	// 获取处理状态
	clusterQueryParams := metaentity.ClusterQueryParams{}
	clusterQueryParams.ClusterName = data.ClusterName
	clusterQueryParams.Namespace = data.Namespace
	crdClusterEntity, err := c.clusterMetaProvider.FindByParams(&clusterQueryParams)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterError, err))
		return
	}

	opsRequestParams := &metaentity.OpsRequestQueryParams{}
	opsRequestParams.CrdClusterID = crdClusterEntity.ID
	opsRequestParams.K8sClusterConfigID = crdClusterEntity.K8sClusterConfigID
	entities, err := c.opsProvider.FindOpsRequestByParams(opsRequestParams)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetOpsRequestStatusError, err))
		return
	}
	// 获取最新的操作记录
	if len(entities) > 0 {
		ops := entities[0]
		opsRequestType := ops.OpsRequestType
		status := ops.Status
		data.ClusterOpsStatus = commutil.GetClusterOpsStatus(
			opsRequestType,
			status,
			data.Status,
		)
	} else {
		data.ClusterOpsStatus = data.Status
	}
}

// ExposeCluster 暴露 cluster 服务
func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	dbsCtx := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.ExposeService,
	}

	responseData, err := c.opsRequestProvider.ExposeCluster(dbsCtx, request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, err))
		return
	}

	// 1s间隔定时器
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	// 30s超时器
	timeout := time.After(30 * time.Second)

	for {
		select {
		// 检查状态
		case <-ticker.C:
			status := c.checkOpsStatusEnded(request, responseData)
			if status {
				coreentity.SuccessResponse(ctx, responseData, commconst.Success)
				return
			}
		// 超时处理
		case <-timeout:
			request.OpsRequestName = responseData.OpsRequestName
			err = c.opsRequestProvider.CancelOpsRequest(request)
			if err != nil {
				coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, err))
				return
			}
			coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ExposeClusterError, fmt.Errorf("expose cluster error")))
			return
		}
	}
}

// checkOpsStatusEnded 检查操作状态是结束状态
func (c *ClusterController) checkOpsStatusEnded(
	request *entity.Request,
	responseData *entity.Metadata,
) bool {
	opsRequestStatus := &entity.Request{
		K8sClusterName: request.K8sClusterName,
		Metadata: entity.Metadata{
			OpsRequestName: responseData.OpsRequestName,
			Namespace:      responseData.Namespace,
		},
	}
	status, err := c.opsRequestProvider.GetOpsRequestStatus(opsRequestStatus)
	if err != nil {
		return true
	}
	if status.Phase == v1alpha1.OpsSucceedPhase ||
		status.Phase == v1alpha1.OpsCancelledPhase ||
		status.Phase == v1alpha1.OpsFailedPhase ||
		status.Phase == v1alpha1.OpsAbortedPhase {
		return true
	}
	return false
}

// UpdateClusterConfig 更新集群组件环境变量
func (c *ClusterController) UpdateClusterConfig(ctx *gin.Context) {
	request := &webreq.ClusterUpdatedRequest{}
	err := ctx.ShouldBindJSON(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	dbsCtx := &commentity.DbsContext{
		BkAuth:      &request.BKAuth,
		RequestType: coreconst.PartialUpdateCluster,
	}

	// 获取集群元数据
	clusterMetaEntity, err := c.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		Namespace:   request.Namespace,
		ClusterName: request.ClusterName,
	})
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterSvcError, err))
		return
	}

	clusterConfig, err := webconfig.ClusterConfBuilderFactory.
		GetBuilder(coreconst.StorageAddonType(clusterMetaEntity.AddonInfo.AddonType)).
		BuildEnvConfig(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateClusterError, err))
		return
	}

	err = c.clusterProvider.UpdateClusterRelease(dbsCtx, clusterConfig, true)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.PartialUpdateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, commconst.Success)
}

// GetClusterConfig 获取cluster config详情
func (c *ClusterController) GetClusterConfig(ctx *gin.Context) {
	var svcEntity entity.K8sSvcEntity
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &svcEntity, nil); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	componentData, err := c.componentProvider.DescribeComponent(&entity.Request{
		K8sClusterName: svcEntity.K8sClusterName,
		Metadata: entity.Metadata{
			ClusterName:   svcEntity.ClusterName,
			Namespace:     svcEntity.Namespace,
			ComponentName: svcEntity.ComponentName,
		},
	})
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeComponentError, err))
		return
	}

	responseData, err := webconfig.ClusterConfBuilderFactory.
		GetBuilder(coreconst.StorageAddonType(componentData.StorageAddonType)).
		ParseEnvConfig(componentData)

	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DescribeComponentError, err))
		return
	}

	coreentity.SuccessResponse(ctx, responseData, commconst.Success)
}
