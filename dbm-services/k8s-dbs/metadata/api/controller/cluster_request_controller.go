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
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metahelper "k8s-dbs/metadata/helper"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	corevo "k8s-dbs/metadata/vo/resp"

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

// ListClusterRecords 根据 k8s_cluster_name, cluster_name, namespace 分页检索集群操作记录.
func (k *ClusterRequestRecordController) ListClusterRecords(ctx *gin.Context) {
	pagination, err := metahelper.BuildPagination(ctx)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
	}
	var searchReqVo req.ClusterRequestRecordSearch
	if err := ctx.ShouldBindJSON(&searchReqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	requestParams := &metaentity.ClusterRequestQueryParams{
		K8sClusterName: searchReqVo.K8sClusterName,
		ClusterName:    searchReqVo.ClusterName,
		NameSpace:      searchReqVo.NameSpace,
	}
	records, count, err := k.clusterRequestProvider.ListRecords(requestParams, pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data []corevo.ClusterRequestRecordRespVo
	if err := copier.Copy(&data, records); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var responseData = corevo.PageResult{
		Count:  count,
		Result: data,
	}
	entity.SuccessResponse(ctx, responseData, commconst.Success)
}
