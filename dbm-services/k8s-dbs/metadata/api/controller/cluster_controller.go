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
	commconst "k8s-dbs/common/constant"
	commhelper "k8s-dbs/common/helper"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/response"
	"reflect"
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

// ClusterController manages metadata for cluster.
type ClusterController struct {
	clusterProvider provider.K8sCrdClusterProvider
}

// NewClusterController creates a new instance of cluster.
func NewClusterController(clusterProvider provider.K8sCrdClusterProvider) *ClusterController {
	return &ClusterController{clusterProvider}
}

// GetCluster retrieves a cluster by its ID.
func (c *ClusterController) GetCluster(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	cluster, err := c.clusterProvider.FindClusterByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data response.K8sCrdClusterResponse
	if err := copier.Copy(&data, cluster); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	data.BkBizTitle = fmt.Sprintf("[%d]%s", data.BkBizID, data.BkBizName)
	data.TopoNameAlias = getTopoNameAlias(data.AddonInfo.AddonType, data.TopoName)
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// ListCluster retrieves a clusters by params and pagination.
func (c *ClusterController) ListCluster(ctx *gin.Context) {
	pagination, err := commhelper.BuildPagination(ctx)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var clusterQueryParams metaentity.ClusterQueryParams
	if err := commhelper.DecodeParams(ctx, commhelper.BuildParams, &clusterQueryParams,
		map[string]reflect.Type{"bkBizId": reflect.TypeOf(uint64(0))}); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetClusterEventError, err))
		return
	}
	clusterEntities, count, err := c.clusterProvider.ListClusters(&clusterQueryParams, pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
	}
	var data []response.K8sCrdClusterResponse
	if err := copier.Copy(&data, clusterEntities); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
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
	entity.SuccessResponse(ctx, responseData, commconst.Success)
}
