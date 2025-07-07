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

// K8sCrdComponentProvider 定义 component 业务逻辑层访问接口
type K8sCrdComponentProvider interface {
	CreateComponent(entity *entitys.K8sCrdComponentEntity) (*entitys.K8sCrdComponentEntity, error)
	DeleteComponentByID(id uint64) (uint64, error)
	FindComponentByID(id uint64) (*entitys.K8sCrdComponentEntity, error)
	UpdateComponent(entity *entitys.K8sCrdComponentEntity) (uint64, error)
	DeleteComponentByClusterID(id uint64) (uint64, error)
}

// K8sCrdComponentProviderImpl K8sCrdComponentProvider 具体实现
type K8sCrdComponentProviderImpl struct {
	dbAccess dbaccess.K8sCrdComponentDbAccess
}

// DeleteComponentByClusterID 根据 cluster ID 来删除 component
func (k K8sCrdComponentProviderImpl) DeleteComponentByClusterID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByClusterID(id)
}

// CreateComponent 创建 component
func (k K8sCrdComponentProviderImpl) CreateComponent(entity *entitys.K8sCrdComponentEntity) (
	*entitys.K8sCrdComponentEntity, error,
) {
	k8sCrdComponentModel := models.K8sCrdComponentModel{}
	err := copier.Copy(&k8sCrdComponentModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	componentModel, err := k.dbAccess.Create(&k8sCrdComponentModel)
	if err != nil {
		slog.Error("Failed to create entity", "error", err)
		return nil, err
	}
	componentEntity := entitys.K8sCrdComponentEntity{}
	if err := copier.Copy(&componentEntity, componentModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &componentEntity, nil
}

// DeleteComponentByID 删除 component
func (k K8sCrdComponentProviderImpl) DeleteComponentByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindComponentByID 查找 component
func (k K8sCrdComponentProviderImpl) FindComponentByID(id uint64) (*entitys.K8sCrdComponentEntity, error) {
	componentModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	componentEntity := entitys.K8sCrdComponentEntity{}
	if err := copier.Copy(&componentEntity, componentModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &componentEntity, nil
}

// UpdateComponent 更新 component
func (k K8sCrdComponentProviderImpl) UpdateComponent(entity *entitys.K8sCrdComponentEntity) (uint64, error) {
	componentModel := models.K8sCrdComponentModel{}
	err := copier.Copy(&componentModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&componentModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdComponentProvider 创建 K8sCrdComponentDbAccess 接口实现实例
func NewK8sCrdComponentProvider(dbAccess dbaccess.K8sCrdComponentDbAccess) K8sCrdComponentProvider {
	return &K8sCrdComponentProviderImpl{dbAccess}
}
