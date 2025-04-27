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
	"log/slog"

	"github.com/jinzhu/copier"
)

// K8sCrdClusterDefinitionProvider 定义 cd 业务逻辑层访问接口
type K8sCrdClusterDefinitionProvider interface {
	CreateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (*entitys.K8sCrdClusterDefinitionEntity, error)
	DeleteClusterDefinitionByID(id uint64) (uint64, error)
	FindClusterDefinitionByID(id uint64) (*entitys.K8sCrdClusterDefinitionEntity, error)
	UpdateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (uint64, error)
}

// K8sCrdClusterDefinitionProviderImpl K8sCrdClusterDefinitionProvider 具体实现
type K8sCrdClusterDefinitionProviderImpl struct {
	dbAccess dbaccess.K8sCrdClusterDefinitionDbAccess
}

// CreateClusterDefinition 创建 cd
func (k *K8sCrdClusterDefinitionProviderImpl) CreateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (
	*entitys.K8sCrdClusterDefinitionEntity, error,
) {
	cdModel := models.K8sCrdClusterDefinitionModel{}
	err := copier.Copy(&cdModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model")
		return nil, err
	}
	addedCdModel, err := k.dbAccess.Create(&cdModel)
	if err != nil {
		slog.Error("Failed to create model")
		return nil, err
	}
	cdEntity := entitys.K8sCrdClusterDefinitionEntity{}
	if err := copier.Copy(&cdEntity, addedCdModel); err != nil {
		slog.Error("Failed to copy entity to copied model")
		return nil, err
	}
	return &cdEntity, nil
}

// DeleteClusterDefinitionByID 删除 cd
func (k *K8sCrdClusterDefinitionProviderImpl) DeleteClusterDefinitionByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindClusterDefinitionByID 查找 cd
func (k *K8sCrdClusterDefinitionProviderImpl) FindClusterDefinitionByID(id uint64) (
	*entitys.K8sCrdClusterDefinitionEntity, error,
) {
	cdModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	cdEntity := entitys.K8sCrdClusterDefinitionEntity{}
	if err := copier.Copy(&cdEntity, cdModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &cdEntity, nil
}

// UpdateClusterDefinition 更新 cd
func (k *K8sCrdClusterDefinitionProviderImpl) UpdateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (
	uint64, error,
) {
	cdModel := models.K8sCrdClusterDefinitionModel{}
	err := copier.Copy(&cdModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&cdModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdClusterDefinitionProvider 创建 K8sCrdClusterDefinitionProvider 接口实现实例
func NewK8sCrdClusterDefinitionProvider(
	dbAccess dbaccess.K8sCrdClusterDefinitionDbAccess,
) K8sCrdClusterDefinitionProvider {
	return &K8sCrdClusterDefinitionProviderImpl{dbAccess}
}
