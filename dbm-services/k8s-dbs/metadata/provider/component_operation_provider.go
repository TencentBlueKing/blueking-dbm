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

package provider

import (
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/dbaccess"
	metaenitty "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"log/slog"

	"github.com/jinzhu/copier"
)

// ComponentOperationProvider 定义 component operation 业务逻辑层访问接口
type ComponentOperationProvider interface {
	CreateComponentOperation(entity *metaenitty.ComponentOperationEntity) (*metaenitty.ComponentOperationEntity, error)
	ListComponentOperations(pagination entity.Pagination) ([]*metaenitty.ComponentOperationEntity, error)
}

// ComponentOperationProviderImpl ComponentOperationProvider 具体实现
type ComponentOperationProviderImpl struct {
	componentOpDBAccess dbaccess.ComponentOperationDbAccess
	opDefDBAccess       dbaccess.OperationDefinitionDbAccess
}

// CreateComponentOperation 创建 component operation
func (o *ComponentOperationProviderImpl) CreateComponentOperation(entity *metaenitty.ComponentOperationEntity) (
	*metaenitty.ComponentOperationEntity, error,
) {
	model := models.ComponentOperationModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := o.componentOpDBAccess.Create(&model)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := metaenitty.ComponentOperationEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// ListComponentOperations 获取 component operation 列表
func (o *ComponentOperationProviderImpl) ListComponentOperations(pagination entity.Pagination) (
	[]*metaenitty.ComponentOperationEntity,
	error,
) {
	componentOpModels, _, err := o.componentOpDBAccess.ListByPage(pagination)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	var componentOpEntities []*metaenitty.ComponentOperationEntity
	if err := copier.Copy(&componentOpEntities, componentOpModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}

	for i, op := range componentOpEntities {
		opDefModel, err := o.opDefDBAccess.FindByID(op.OperationID)
		if err != nil {
			return nil, err
		}
		opDefEntity := metaenitty.OperationDefinitionEntity{}
		if err := copier.Copy(&opDefEntity, opDefModel); err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		}
		componentOpEntities[i].Operation = opDefEntity
	}
	return componentOpEntities, nil
}

// NewComponentOperationProvider 创建 ComponentOperationProvider 接口实现实例
func NewComponentOperationProvider(componentOpDBAccess dbaccess.ComponentOperationDbAccess,
	opDefDBAccess dbaccess.OperationDefinitionDbAccess) ComponentOperationProvider {
	return &ComponentOperationProviderImpl{componentOpDBAccess, opDefDBAccess}
}
