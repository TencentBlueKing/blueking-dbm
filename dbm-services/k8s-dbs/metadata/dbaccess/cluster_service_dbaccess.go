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

package dbaccess

import (
	"fmt"
	"k8s-dbs/common/entity"
	models "k8s-dbs/metadata/dbaccess/model"
	"log/slog"

	"gorm.io/gorm"
)

// K8sClusterServiceDbAccess 定义 clsuter servcie 元数据的数据库访问接口
type K8sClusterServiceDbAccess interface {
	Create(model *models.K8sClusterServiceModel) (*models.K8sClusterServiceModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sClusterServiceModel, error)
	Update(model *models.K8sClusterServiceModel) (uint64, error)
	ListByPage(pagination entity.Pagination) ([]models.K8sClusterServiceModel, int64, error)
}

// K8sClusterServiceDbAccessImpl K8sClusterServiceDbAccess 的具体实现
type K8sClusterServiceDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) Create(model *models.K8sClusterServiceModel) (
	*models.K8sClusterServiceModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create service error", "error", err)
		return nil, err
	}
	var addedService models.K8sClusterServiceModel
	if err := k.db.First(&addedService, "id=?", model.ID).Error; err != nil {
		slog.Error("Find service error", "error", err)
		return nil, err
	}
	return &addedService, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sClusterServiceModel{}, id)
	if result.Error != nil {
		slog.Error("Delete service error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) FindByID(id uint64) (*models.K8sClusterServiceModel, error) {
	var request models.K8sClusterServiceModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		slog.Error("Find service error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &request, nil
}

// Update 更新元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) Update(model *models.K8sClusterServiceModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update service error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) ListByPage(_ entity.Pagination) (
	[]models.K8sClusterServiceModel,
	int64,
	error,
) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sClusterServiceDbAccess 创建 K8sClusterServiceDbAccess 接口实现实例
func NewK8sClusterServiceDbAccess(db *gorm.DB) K8sClusterServiceDbAccess {
	return &K8sClusterServiceDbAccessImpl{db: db}
}
