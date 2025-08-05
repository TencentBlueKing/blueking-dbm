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
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	corevo "k8s-dbs/metadata/vo/response"
	"time"

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
	pagination, err := commutil.BuildPagination(ctx)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestParams, err := k.buildListParams(ctx)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	records, count, err := k.clusterRequestProvider.ListRecords(requestParams, pagination)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []corevo.ClusterOperationLogResponse
	if err := copier.Copy(&data, records); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var responseData = corevo.PageResult{
		Count:  count,
		Result: data,
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

func (k *ClusterRequestRecordController) buildListParams(ctx *gin.Context) (
	*metaentity.ClusterRequestQueryParams,
	error,
) {
	startTimeStr := ctx.Query("startTime")
	startTime, err := time.Parse(time.DateTime, startTimeStr)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.ParameterValueError, err)
	}
	endTimeStr := ctx.Query("endTime")
	endTime, err := time.Parse(time.DateTime, endTimeStr)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.ParameterValueError, err)
	}
	requestPrams := metaentity.ClusterRequestQueryParams{
		ClusterNames:   ctx.QueryArray("clusterName"),
		Operators:      ctx.QueryArray("operator"),
		RequestTypes:   ctx.QueryArray("requestType"),
		RequestParams:  ctx.Query("requestParams"),
		K8sClusterName: ctx.Query("k8sClusterName"),
		NameSpace:      ctx.Query("nameSpace"),
		StartTime:      startTime,
		EndTime:        endTime,
	}
	return &requestPrams, nil
}
