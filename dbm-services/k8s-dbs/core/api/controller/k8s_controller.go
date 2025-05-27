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
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"

	reqvo "k8s-dbs/core/api/vo/req"

	respvo "k8s-dbs/core/api/vo/resp"

	pventity "k8s-dbs/core/provider/entity"
)

// K8sController k8s 集群管理 controller
type K8sController struct {
	k8sProvider *provider.K8sProvider
}

// CreateNamespace 创建 namespace
func (k *K8sController) CreateNamespace(ctx *gin.Context) {
	var namespaceReq reqvo.K8sNsReqVo
	if err := ctx.ShouldBindJSON(&namespaceReq); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateK8sNsError, err))
		return
	}
	var namespaceEntity pventity.K8sNamespaceEntity
	if err := copier.Copy(&namespaceEntity, &namespaceReq); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateK8sNsError, err))
		return
	}
	added, err := k.k8sProvider.CreateNamespace(&namespaceEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateK8sNsError, err))
		return
	}
	var data respvo.K8sNamespaceRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateK8sNsError, err))
		return
	}
	entity.SuccessResponse(ctx, data, "OK")
}

// NewK8sController 构建 K8sController
func NewK8sController(k8sProvider *provider.K8sProvider) *K8sController {
	return &K8sController{
		k8sProvider,
	}
}
