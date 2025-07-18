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
	coreconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	commhelper "k8s-dbs/common/helper"
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
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	var namespaceEntity entity.K8sNamespaceEntity
	if err := copier.Copy(&namespaceEntity, &namespaceReq); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &namespaceReq.BKAuth,
	}
	added, err := k.k8sProvider.CreateNamespace(&dbsContext, &namespaceEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	var data response.K8sNamespaceResponse
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateK8sNsError, err))
		return
	}
	entity.SuccessResponse(ctx, data, coreconst.Success)
}

// ListPodLogs 获取 pod 日志分页结果
func (k *K8sController) ListPodLogs(ctx *gin.Context) {
	pagination, err := commhelper.BuildPagination(ctx)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var podLogEntity entity.K8sPodLogQueryParams
	if err := commhelper.DecodeParams(ctx, commhelper.BuildParams, &podLogEntity, nil); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	logs, count, err := k.k8sProvider.ListPodLogs(&podLogEntity, pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetPodLogError, err))
		return
	}
	var responseData = metarespvo.PageResult{
		Count:  count,
		Result: logs,
	}
	entity.SuccessResponse(ctx, responseData, coreconst.Success)
}

// GetPodDetail 获取实例详情
func (k *K8sController) GetPodDetail(ctx *gin.Context) {
	var podDetailParams entity.K8sPodDetailQueryParams
	if err := commhelper.DecodeParams(ctx, commhelper.BuildParams, &podDetailParams, nil); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	podDetail, err := k.k8sProvider.GetPodDetail(&podDetailParams)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetPodDetailError, err))
		return
	}

	entity.SuccessResponse(ctx, podDetail, coreconst.Success)

}

// NewK8sController 构建 K8sController
func NewK8sController(k8sProvider *provider.K8sProvider) *K8sController {
	return &K8sController{
		k8sProvider,
	}
}
