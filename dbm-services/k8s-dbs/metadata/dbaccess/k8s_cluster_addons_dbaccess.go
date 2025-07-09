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
	"errors"
	"fmt"
	commentity "k8s-dbs/common/entity"
	mconst "k8s-dbs/metadata/constant"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// K8sClusterAddonsDbAccess 定义 k8s cluster addon 元数据的数据库访问接口
type K8sClusterAddonsDbAccess interface {
	Create(model *metamodel.K8sClusterAddonsModel) (*metamodel.K8sClusterAddonsModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.K8sClusterAddonsModel, error)
	Update(model *metamodel.K8sClusterAddonsModel) (uint64, error)
	ListByPage(pagination commentity.Pagination) ([]metamodel.K8sClusterAddonsModel, int64, error)
	FindByParams(params *metaentity.K8sClusterAddonQueryParams) ([]metamodel.K8sClusterAddonsModel, error)
}

// K8sClusterAddonsDbAccessImpl K8sClusterAddonsDbAccess 的具体实现
type K8sClusterAddonsDbAccessImpl struct {
	db *gorm.DB
}

// FindByParams 通过参数查询
func (k *K8sClusterAddonsDbAccessImpl) FindByParams(
	params *metaentity.K8sClusterAddonQueryParams,
) ([]metamodel.K8sClusterAddonsModel, error) {
	var addons []metamodel.K8sClusterAddonsModel
	if err := k.db.
		Where(params).
		Limit(mconst.MaxFetchSize).
		Find(&addons).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return []metamodel.K8sClusterAddonsModel{}, nil
		}
		slog.Error("failed to find by params", "error", err)
		return nil, fmt.Errorf("database query failed: %w", err)
	}
	return addons, nil
}

// Create 创建 addon 元数据接口实现
func (k *K8sClusterAddonsDbAccessImpl) Create(storageAddonModel *metamodel.K8sClusterAddonsModel) (
	*metamodel.K8sClusterAddonsModel, error,
) {
	if err := k.db.Create(storageAddonModel).Error; err != nil {
		slog.Error("Create storageAddon error", "error", err)
		return nil, err
	}
	return storageAddonModel, nil
}

// DeleteByID 删除 addon 元数据接口实现
func (k *K8sClusterAddonsDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&metamodel.K8sClusterAddonsModel{}, id)
	if result.Error != nil {
		slog.Error("Delete storageAddon error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 addon 元数据接口实现
func (k *K8sClusterAddonsDbAccessImpl) FindByID(id uint64) (*metamodel.K8sClusterAddonsModel, error) {
	var storageAddonModel metamodel.K8sClusterAddonsModel
	result := k.db.First(&storageAddonModel, id)
	if result.Error != nil {
		slog.Error("Find storageAddon error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &storageAddonModel, nil
}

// Update 更新 addon 元数据接口实现
func (k *K8sClusterAddonsDbAccessImpl) Update(storageAddonModel *metamodel.K8sClusterAddonsModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(storageAddonModel)
	if result.Error != nil {
		slog.Error("failed to find by params", "error", result.Error)
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 addon 元数据接口实现
func (k *K8sClusterAddonsDbAccessImpl) ListByPage(pagination commentity.Pagination) (
	[]metamodel.K8sClusterAddonsModel,
	int64,
	error,
) {
	var clusterAddonModel []metamodel.K8sClusterAddonsModel
	if err := k.db.Offset(pagination.Page).Limit(pagination.Limit).
		Where("active=1").Find(&clusterAddonModel).Error; err != nil {
		slog.Error("List storageAddon error", "error", err.Error())
		return nil, 0, err
	}
	return clusterAddonModel, int64(len(clusterAddonModel)), nil
}

// NewK8sClusterAddonsDbAccess 创建 K8sClusterAddonsDbAccess 接口实现实例
func NewK8sClusterAddonsDbAccess(db *gorm.DB) K8sClusterAddonsDbAccess {
	return &K8sClusterAddonsDbAccessImpl{db: db}
}
