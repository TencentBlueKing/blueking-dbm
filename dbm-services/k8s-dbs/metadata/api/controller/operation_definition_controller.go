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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	metaconst "k8s-dbs/metadata/constant"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// OperationDefinitionController manages metadata for operation definition.
type OperationDefinitionController struct {
	provider provider.OperationDefinitionProvider
}

// NewOperationDefinitionController creates a new instance of OperationDefinitionController.
func NewOperationDefinitionController(provider provider.OperationDefinitionProvider) *OperationDefinitionController {
	return &OperationDefinitionController{provider}
}

// ListOperationDefinitions list operation definitions
func (o *OperationDefinitionController) ListOperationDefinitions(ctx *gin.Context) {
	sizeStr := ctx.DefaultQuery("size", metaconst.DefaultFetchSizeStr)
	fetchSize, err := strconv.Atoi(sizeStr)
	if err != nil {
		fetchSize = metaconst.DefaultFetchSize // 如果转换失败，使用默认值
	}
	fetchSize = min(fetchSize, metaconst.MaxFetchSize)
	pagination := commentity.Pagination{Limit: fetchSize}
	opDefs, err := o.provider.ListOperationDefinitions(pagination)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.OperationDefinitionRespVo
	if err := copier.Copy(&data, opDefs); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateOperationDefinition creates a new operation definition.
func (o *OperationDefinitionController) CreateOperationDefinition(ctx *gin.Context) {
	var reqVo req.OperationDefinitionReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var definitionEntity entitys.OperationDefinitionEntity
	if err := copier.Copy(&definitionEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := o.provider.CreateOperationDefinition(&definitionEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.OperationDefinitionRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
