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
	webreq "k8s-dbs/dataweb/vo/request"
	"k8s-dbs/dataweb/vo/response"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"strconv"

	"github.com/jinzhu/copier"

	"github.com/gin-gonic/gin"
)

// ClusterController 存储集群管理 Controller
type ClusterController struct {
	clusterProvider     *provider.ClusterProvider
	opsRequestProvider  *provider.OpsRequestProvider
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
	opsProvider         metaprovider.K8sCrdOpsRequestProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(
	clusterProvider *provider.ClusterProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	opsProvider metaprovider.K8sCrdOpsRequestProvider,
	opsRequestProvider *provider.OpsRequestProvider,
) *ClusterController {
	return &ClusterController{
		clusterProvider:     clusterProvider,
		clusterMetaProvider: clusterMetaProvider,
		opsProvider:         opsProvider,
		opsRequestProvider:  opsRequestProvider,
	}
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &webreq.ClusterInstallRequest{}
	if err := ctx.ShouldBindJSON(request); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	clusterConfig, err := ClusterConfBuilderFactory.
		GetBuilder(request.BasicInfo.StorageAddonType).
		BuildConfig(request)
	if err != nil {
		slog.Error("convert to cluster config error", "clusterInstall", request, "err", err)
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
	requestParams, err := commutil.BuildListParams(ctx)
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

	var responseData = response.PageResult{
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
		slog.Error("failed to find cluster by param", "err", err)
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterError, err))
		return
	}

	opsRequestParams := &metaentity.OpsRequestQueryParams{}
	opsRequestParams.CrdClusterID = crdClusterEntity.ID
	opsRequestParams.K8sClusterConfigID = crdClusterEntity.K8sClusterConfigID
	entities, err := c.opsProvider.FindOpsRequestByParams(opsRequestParams)
	if err != nil {
		slog.Error("failed to find ops request by param", "err", err)
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetOpsRequestStatusError, err))
		return
	}
	// 获取最新的操作记录
	if len(entities) > 0 {
		ops := entities[0]
		opsRequestType := ops.OpsRequestType
		opsRequest := entity.Request{}
		opsRequest.K8sClusterName = data.K8sClusterConfig.ClusterName
		opsRequest.Metadata.OpsRequestName = ops.OpsRequestName
		opsRequest.Metadata.Namespace = data.Namespace
		opsRequestData, err := c.opsRequestProvider.DescribeOpsRequest(&opsRequest)
		if err != nil {
			data.ClusterOpsStatus = data.Status
			slog.Warn("failed to describe ops request", "err", err)
		} else {
			data.ClusterOpsStatus = commutil.GetClusterOpsStatus(
				opsRequestType,
				string(opsRequestData.OpsRequestStatus.Phase),
				data.Status,
			)
		}
	} else {
		data.ClusterOpsStatus = data.Status
	}
}
