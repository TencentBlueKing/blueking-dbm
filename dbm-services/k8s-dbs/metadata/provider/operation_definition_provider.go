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
	"k8s-dbs/metadata/dbaccess"
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"github.com/jinzhu/copier"
)

// OperationDefinitionProvider 定义 operation definition 业务逻辑层访问接口
type OperationDefinitionProvider interface {
	CreateOperationDefinition(entity *entitys.OperationDefinitionEntity) (*entitys.OperationDefinitionEntity, error)
	ListOperationDefinitions(pagination utils.Pagination) ([]entitys.OperationDefinitionEntity, error)
}

// OperationDefinitionProviderImpl OperationDefinitionProvider 具体实现
type OperationDefinitionProviderImpl struct {
	dbAccess dbaccess.OperationDefinitionDbAccess
}

// CreateOperationDefinition 创建 operation definition
func (o *OperationDefinitionProviderImpl) CreateOperationDefinition(entity *entitys.OperationDefinitionEntity) (
	*entitys.OperationDefinitionEntity, error,
) {
	definitionModel := models.OperationDefinitionModel{}
	err := copier.Copy(&definitionModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := o.dbAccess.Create(&definitionModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.OperationDefinitionEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// ListOperationDefinitions 获取 operation definition 列表
func (o *OperationDefinitionProviderImpl) ListOperationDefinitions(pagination utils.Pagination) (
	[]entitys.OperationDefinitionEntity,
	error,
) {
	definitionModels, _, err := o.dbAccess.ListByPage(pagination)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	var definitionEntities []entitys.OperationDefinitionEntity
	if err := copier.Copy(&definitionEntities, definitionModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return definitionEntities, nil
}

// NewOperationDefinitionProvider 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewOperationDefinitionProvider(dbAccess dbaccess.OperationDefinitionDbAccess) OperationDefinitionProvider {
	return &OperationDefinitionProviderImpl{dbAccess: dbAccess}
}
