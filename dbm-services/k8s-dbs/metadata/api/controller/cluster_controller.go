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
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	"k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/response"
	"log/slog"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

var topoNameAliasMapping = map[string]map[string]string{
	"victoriametrics": {
		"cluster": "全套服务",
		"select":  "查询服务",
	},
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

// ClusterController 负责管理维护存储集群元数据
type ClusterController struct {
	clusterProvider provider.K8sCrdClusterProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(clusterProvider provider.K8sCrdClusterProvider) *ClusterController {
	return &ClusterController{clusterProvider}
}

// GetClusterTopology 按照 ID 获取集群实例拓扑
func (c *ClusterController) GetClusterTopology(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterTopologyDetail)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	clusterTopology, err := c.clusterProvider.FindClusterTopology(id)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, clusterTopology, commconst.Success)
}

// respondCluster 根据 ID 查找 cluster 实体，转换为响应并返回
func (c *ClusterController) respondCluster(ctx *gin.Context, id uint64) {
	cluster, err := c.clusterProvider.FindClusterByID(id)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data response.K8sCrdClusterResponse
	if err := copier.Copy(&data, cluster); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	data.BkBizTitle = fmt.Sprintf("[%d]%s", data.BkBizID, data.BkBizName)
	data.TopoNameAlias = getTopoNameAlias(data.AddonInfo.AddonType, data.TopoName)
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetClusterInfoByClusterID 按照 cluster_id（dbm_cluster_id）获取存储集群实例
func (c *ClusterController) GetClusterInfoByClusterID(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterDetailByClusterID)
	clusterIDParam := ctx.Param("cluster_id")
	clusterID, err := strconv.ParseUint(clusterIDParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	clusterInfo, err := c.clusterProvider.FindByParams(&entity.ClusterQueryParams{DbmClusterID: clusterID})
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	if clusterInfo == nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError,
			fmt.Errorf("cluster not found with cluster_id %d", clusterID)))
		return
	}
	c.respondCluster(ctx, clusterInfo.ID)
}

// GetClusterInfo 按照 ID 获取存储集群实例
func (c *ClusterController) GetClusterInfo(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterDetail)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	c.respondCluster(ctx, id)
}

// ListCluster 分页检索集群实例列表
func (c *ClusterController) ListCluster(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterList)
	pagination, err := commutil.BuildPagination(ctx)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestParams, err := commutil.BuildClusterListParams(ctx)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	clusterEntities, count, err := c.clusterProvider.ListClusters(requestParams, pagination)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []response.K8sCrdClusterResponse
	if err = copier.Copy(&data, clusterEntities); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	for idx, clusterEntity := range data {
		data[idx].BkBizTitle = fmt.Sprintf("[%d]%s", clusterEntity.BkBizID, clusterEntity.BkBizName)
		data[idx].TopoNameAlias = getTopoNameAlias(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	}
	var responseData = response.PageResult{
		Count:  count,
		Result: data,
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// UpdateCluster 外部系统传入参数更新集群元数据
func (c *ClusterController) UpdateCluster(ctx *gin.Context) {
	var req provider.UpdateClusterMetadataRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		api.HandleValidationError(ctx, err, &req)
		return
	}

	clusterEntity, err := c.clusterProvider.FindByParams(&entity.ClusterQueryParams{
		Namespace:   req.Namespace,
		ClusterName: req.ClusterName,
	})
	if err != nil {
		slog.Error("获取集群失败", "error", err)
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	if clusterEntity == nil {
		notFoundErr := fmt.Errorf("集群不存在 (clusterName=%s, namespace=%s)", req.ClusterName, req.Namespace)
		slog.Error("获取集群失败", "error", notFoundErr)
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, notFoundErr))
		return
	}

	req.ApplyTo(clusterEntity)

	if _, err := c.clusterProvider.UpdateCluster(clusterEntity); err != nil {
		slog.Error("更新集群元数据失败", "error", err)
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, nil, "更新集群元数据成功")
}
