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
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	"k8s-dbs/core/vo/request"
	"k8s-dbs/core/vo/response"
	"k8s-dbs/errors"
	metarespvo "k8s-dbs/metadata/vo/response"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// K8sController k8s 集群管理 controller
type K8sController struct {
	k8sProvider *provider.K8sProvider
}

// CreateNamespace 创建 namespace
func (k *K8sController) CreateNamespace(ctx *gin.Context) {
	var namespaceReq request.K8sNamespaceRequest
	if err := ctx.ShouldBindJSON(&namespaceReq); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	var namespaceEntity entity.K8sNamespaceEntity
	if err := copier.Copy(&namespaceEntity, &namespaceReq); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &namespaceReq.BKAuth,
	}
	added, err := k.k8sProvider.CreateNamespace(&dbsContext, &namespaceEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	var data response.K8sNamespaceResponse
	if err := copier.Copy(&data, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// ListPodLogs 获取 pod 日志分页结果
func (k *K8sController) ListPodLogs(ctx *gin.Context) {
	pagination, err := commutil.BuildPagination(ctx)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var podLogEntity entity.K8sPodLogQueryParams
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &podLogEntity, nil); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	logs, count, err := k.k8sProvider.ListPodLogs(&podLogEntity, pagination)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetPodLogError, err))
		return
	}
	var responseData = metarespvo.PageResult{
		Count:  count,
		Result: logs,
	}
	api.SuccessResponse(ctx, responseData, commconst.Success)
}

// GetPodRawLogs 获取 pod 日志原始日志
func (k *K8sController) GetPodRawLogs(ctx *gin.Context) {
	var podLogQueryEntity entity.K8sPodLogQueryParams
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &podLogQueryEntity, nil); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	data, err := k.k8sProvider.GetPodRawLogs(&podLogQueryEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetPodLogError, err))
		return
	}
	api.SuccessResponse(ctx, data, commconst.Success)
}

// GetPodDetail 获取实例详情
func (k *K8sController) GetPodDetail(ctx *gin.Context) {
	var podDetailParams entity.K8sPodDetailQueryParams
	if err := commutil.DecodeParams(ctx, commutil.BuildParams, &podDetailParams, nil); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	podDetail, err := k.k8sProvider.GetPodDetail(&podDetailParams)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetPodDetailError, err))
		return
	}
	api.SuccessResponse(ctx, podDetail, commconst.Success)
}

// DeletePod 删除实例
func (k *K8sController) DeletePod(ctx *gin.Context) {
	var podDeleteParams request.K8sPodDeleteRequest
	if err := ctx.ShouldBindJSON(&podDeleteParams); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteK8sPodError, err))
		return
	}
	var podDeleteEntity entity.K8sPodDelete
	if err := copier.Copy(&podDeleteEntity, &podDeleteParams); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth:      &podDeleteParams.BKAuth,
		RequestType: coreconst.DeleteK8sPod,
	}
	err := k.k8sProvider.DeletePod(&dbsContext, &podDeleteEntity)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteK8sPodError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// NewK8sController 构建 K8sController
func NewK8sController(k8sProvider *provider.K8sProvider) *K8sController {
	return &K8sController{
		k8sProvider,
	}
}
