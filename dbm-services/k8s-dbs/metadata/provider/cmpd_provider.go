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

// K8sCrdCmpdProvider 定义 cmpd 业务逻辑层访问接口
type K8sCrdCmpdProvider interface {
	CreateCmpd(entity *entitys.K8sCrdComponentDefinitionEntity) (
		*entitys.K8sCrdComponentDefinitionEntity, error)
	DeleteCmpdByID(id uint64) (uint64, error)
	FindCmpdByID(id uint64) (*entitys.K8sCrdComponentDefinitionEntity, error)
	UpdateCmpd(entity *entitys.K8sCrdComponentDefinitionEntity) (uint64, error)
}

// K8sCrdComponentDefinitionProviderImpl K8sCrdCmpdProvider 具体实现
type K8sCrdComponentDefinitionProviderImpl struct {
	dbAccess dbaccess.K8sCrdCmpdDbAccess
}

// CreateCmpd 创建 cmpd
func (k *K8sCrdComponentDefinitionProviderImpl) CreateCmpd(
	cmpd *entitys.K8sCrdComponentDefinitionEntity) (
	*entitys.K8sCrdComponentDefinitionEntity, error,
) {
	K8sCrdComponentDefinitionModel := models.K8sCrdComponentDefinitionModel{}
	err := copier.Copy(&K8sCrdComponentDefinitionModel, cmpd)
	if err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	addedCmpdModel, err := k.dbAccess.Create(&K8sCrdComponentDefinitionModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	componentDefinitionEntity := entitys.K8sCrdComponentDefinitionEntity{}
	if err := copier.Copy(&componentDefinitionEntity, addedCmpdModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &componentDefinitionEntity, nil
}

// DeleteCmpdByID 删除 cmpd
func (k *K8sCrdComponentDefinitionProviderImpl) DeleteCmpdByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindCmpdByID 查找 cmpd
func (k *K8sCrdComponentDefinitionProviderImpl) FindCmpdByID(id uint64) (
	*entitys.K8sCrdComponentDefinitionEntity, error,
) {
	componentDefinitionModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to delete model", "error", err)
		return nil, err
	}
	componentDefinitionEntity := entitys.K8sCrdComponentDefinitionEntity{}
	if err := copier.Copy(&componentDefinitionEntity, componentDefinitionModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &componentDefinitionEntity, nil
}

// UpdateCmpd 更新 cmpd
func (k *K8sCrdComponentDefinitionProviderImpl) UpdateCmpd(
	componentDefinition *entitys.K8sCrdComponentDefinitionEntity) (
	uint64, error,
) {
	componentDefinitionModel := models.K8sCrdComponentDefinitionModel{}
	err := copier.Copy(&componentDefinitionModel, componentDefinition)
	if err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&componentDefinitionModel)
	if err != nil {
		slog.Error("Failed to update model", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdCmpdProvider 创建 K8sCrdCmpdProvider 接口实现实例
func NewK8sCrdCmpdProvider(
	dbAccess dbaccess.K8sCrdCmpdDbAccess) K8sCrdCmpdProvider {
	return &K8sCrdComponentDefinitionProviderImpl{dbAccess}
}
