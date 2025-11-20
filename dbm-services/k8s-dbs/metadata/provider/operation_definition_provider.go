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
	entitys "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// OperationDefinitionProvider 定义 operation definition 业务逻辑层访问接口
type OperationDefinitionProvider interface {
	CreateOperationDefinition(entity *entitys.OperationDefinitionEntity) (*entitys.OperationDefinitionEntity, error)
	ListOperationDefinitions(pagination entity.Pagination) ([]*entitys.OperationDefinitionEntity, error)
}

// OperationDefinitionProviderImpl OperationDefinitionProvider 具体实现
type OperationDefinitionProviderImpl struct {
	dbAccess dbaccess.OperationDefinitionDbAccess
}

// CreateOperationDefinition 创建 operation definition
func (o *OperationDefinitionProviderImpl) CreateOperationDefinition(entity *entitys.OperationDefinitionEntity) (
	*entitys.OperationDefinitionEntity,
	error,
) {
	definitionModel := models.OperationDefinitionModel{}
	if err := copier.Copy(&definitionModel, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addedModel, err := o.dbAccess.Create(&definitionModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create operation definition with entity %+v", entity)
	}
	addedEntity := entitys.OperationDefinitionEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &addedEntity, nil
}

// ListOperationDefinitions 获取 operation definition 列表
func (o *OperationDefinitionProviderImpl) ListOperationDefinitions(pagination entity.Pagination) (
	[]*entitys.OperationDefinitionEntity,
	error,
) {
	definitionModels, _, err := o.dbAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list operation definitions for pagination %+v", pagination)
	}
	var definitionEntities []*entitys.OperationDefinitionEntity
	if err = copier.Copy(&definitionEntities, definitionModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return definitionEntities, nil
}

// NewOperationDefinitionProvider 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewOperationDefinitionProvider(dbAccess dbaccess.OperationDefinitionDbAccess) OperationDefinitionProvider {
	return &OperationDefinitionProviderImpl{dbAccess: dbAccess}
}
