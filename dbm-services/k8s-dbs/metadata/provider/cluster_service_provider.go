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

// K8sClusterServiceProvider 定义 cluster service 业务逻辑层访问接口
type K8sClusterServiceProvider interface {
	CreateClusterService(entity *entitys.K8sClusterServiceEntity) (*entitys.K8sClusterServiceEntity, error)
	DeleteClusterServiceByID(id uint64) (uint64, error)
	FindClusterServiceByID(id uint64) (*entitys.K8sClusterServiceEntity, error)
	UpdateClusterService(entity *entitys.K8sClusterServiceEntity) (uint64, error)
}

// K8sClusterServiceProviderImpl K8sClusterServiceProvider 具体实现
type K8sClusterServiceProviderImpl struct {
	dbAccess dbaccess.K8sClusterServiceDbAccess
}

// CreateClusterService 创建 cluster service
func (k *K8sClusterServiceProviderImpl) CreateClusterService(entity *entitys.K8sClusterServiceEntity) (
	*entitys.K8sClusterServiceEntity, error,
) {
	newModel := models.K8sClusterServiceModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := k.dbAccess.Create(&newModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.K8sClusterServiceEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// DeleteClusterServiceByID 删除 cluster service
func (k *K8sClusterServiceProviderImpl) DeleteClusterServiceByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindClusterServiceByID 查找 cluster service
func (k *K8sClusterServiceProviderImpl) FindClusterServiceByID(id uint64) (*entitys.K8sClusterServiceEntity, error) {
	foundModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	foundEntity := entitys.K8sClusterServiceEntity{}
	if err := copier.Copy(&foundEntity, foundModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &foundEntity, nil
}

// UpdateClusterService 更新 cluster service
func (k *K8sClusterServiceProviderImpl) UpdateClusterService(entity *entitys.K8sClusterServiceEntity) (uint64, error) {
	newModel := models.K8sClusterServiceModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&newModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sClusterServiceProvider 创建 K8sClusterServiceProvider 接口实现实例
func NewK8sClusterServiceProvider(dbAccess dbaccess.K8sClusterServiceDbAccess) K8sClusterServiceProvider {
	return &K8sClusterServiceProviderImpl{dbAccess: dbAccess}
}
