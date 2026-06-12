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
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	metareq "k8s-dbs/metadata/vo/request"
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
	ctx.Set(commconst.APIName, commconst.APIMetaClusterRequestList)
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
	if err = copier.Copy(&data, records); err != nil {
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
	var startTime, endTime time.Time
	var err error

	startTimeStr := ctx.Query("startTime")
	if startTimeStr != "" {
		startTime, err = time.Parse(time.DateTime, startTimeStr)
		if err != nil {
			return nil, errors.NewK8sDbsError(errors.ParameterValueError, err)
		}
	}
	endTimeStr := ctx.Query("endTime")
	if endTimeStr != "" {
		endTime, err = time.Parse(time.DateTime, endTimeStr)
		if err != nil {
			return nil, errors.NewK8sDbsError(errors.ParameterValueError, err)
		}
	}
	// 如果 startTime 或 endTime 为空，则不限制时间范围，查询所有数据
	requestPrams := metaentity.ClusterRequestQueryParams{
		ClusterNames:   ctx.QueryArray("clusterName"),
		Creators:       ctx.QueryArray("creator"),
		RequestTypes:   ctx.QueryArray("requestType"),
		RequestParams:  ctx.Query("requestParams"),
		K8sClusterName: ctx.Query("k8sClusterName"),
		NameSpace:      ctx.Query("nameSpace"),
		StartTime:      startTime,
		EndTime:        endTime,
	}
	return &requestPrams, nil
}

// UpdateClusterTicketID 根据 clusterName, k8sClusterName, namespace, requestType 更新 ticketId
func (k *ClusterRequestRecordController) UpdateClusterTicketID(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterRequestUpdate)

	var reqVo metareq.UpdateClusterTicketRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	// 构建查询参数
	params := metaentity.UpdateClusterRequestParams{
		ClusterName:    reqVo.ClusterName,
		K8sClusterName: reqVo.K8sClusterName,
		NameSpace:      reqVo.NameSpace,
		RequestType:    reqVo.RequestType,
	}

	err := k.clusterRequestProvider.AssociateTicketRecord(reqVo.TicketID, &params)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, true, commconst.Success)
}

// CreateClusterRecord 创建集群操作记录
func (k *ClusterRequestRecordController) CreateClusterRecord(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaClusterRequestCreate)
	var req metareq.CreateClusterOperationLogRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		api.HandleValidationError(ctx, err, &req)
		return
	}
	requestBytes, err := json.Marshal(req)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}
	requestRecord := &metaentity.ClusterRequestRecordEntity{
		K8sClusterName: req.K8sClusterName,
		ClusterName:    req.ClusterName,
		NameSpace:      req.NameSpace,
		RequestID:      commutil.RequestID(),
		RequestType:    req.RequestType,
		RequestParams:  string(requestBytes),
		TicketID:       &req.TicketID,
		CreatedBy:      req.BkUserName,
		UpdatedBy:      req.BkUserName,
	}
	addedRequestRecord, err := k.clusterRequestProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	api.SuccessResponse(ctx, addedRequestRecord, commconst.Success)
}
