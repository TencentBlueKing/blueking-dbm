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
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ClusterRequestRecordController manages metadata for addons.
type ClusterRequestRecordController struct {
	clusterRequestProvider provider.ClusterRequestRecordProvider
}

// NewClusterRequestRecordController creates a new instance of ClusterRequestRecordController.
func NewClusterRequestRecordController(
	clusterRequestProvider provider.ClusterRequestRecordProvider,
) *ClusterRequestRecordController {
	return &ClusterRequestRecordController{clusterRequestProvider}
}

// GetRecordsByCluster 根据集群名称来获取对应的集群操作记录.
func (k *ClusterRequestRecordController) GetRecordsByCluster(ctx *gin.Context) {
	k8sClusterName := ctx.Query("k8sClusterName")
	clusterName := ctx.Query("clusterName")
	namespace := ctx.Query("namespace")
	params := map[string]interface{}{
		"k8s_cluster_name": k8sClusterName,
		"cluster_name":     clusterName,
		"namespace":        namespace,
	}
	records, err := k.clusterRequestProvider.FindRecordsByParams(params)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.ClusterRequestRecordRespVo
	if err := copier.Copy(&data, records); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
