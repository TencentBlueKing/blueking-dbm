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
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

// K8sCrdStorageAddonDbAccess 定义 addon 元数据的数据库访问接口
type K8sCrdStorageAddonDbAccess interface {
	Create(model *models.K8sCrdStorageAddonModel) (*models.K8sCrdStorageAddonModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdStorageAddonModel, error)
	Update(model *models.K8sCrdStorageAddonModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdStorageAddonModel, int64, error)
}

// K8sCrdStorageAddonDbAccessImpl K8sCrdStorageAddonDbAccess 的具体实现
type K8sCrdStorageAddonDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) Create(storageAddonModel *models.K8sCrdStorageAddonModel) (
	*models.K8sCrdStorageAddonModel, error,
) {
	if err := k.db.Create(storageAddonModel).Error; err != nil {
		slog.Error("Create storageAddon error", "error", err)
		return nil, err
	}
	var addedStorageAddonModel models.K8sCrdStorageAddonModel
	if err := k.db.First(&addedStorageAddonModel, "addon_name = ?", storageAddonModel.AddonName).Error; err != nil {
		slog.Error("Find storageAddon error", "error", err)
		return nil, err
	}
	return &addedStorageAddonModel, nil
}

// DeleteByID 删除 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdStorageAddonModel{}, id)
	if result.Error != nil {
		slog.Error("Delete storageAddon error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) FindByID(id uint64) (*models.K8sCrdStorageAddonModel, error) {
	var storageAddonModel models.K8sCrdStorageAddonModel
	result := k.db.First(&storageAddonModel, id)
	if result.Error != nil {
		slog.Error("Find storageAddon error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &storageAddonModel, nil
}

// Update 更新 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) Update(storageAddonModel *models.K8sCrdStorageAddonModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(storageAddonModel)
	if result.Error != nil {
		slog.Error("Update storageAddon error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) ListByPage(_ utils.Pagination) (
	[]models.K8sCrdStorageAddonModel,
	int64,
	error,
) {
	// TODO implement me
	panic("implement me")
}

// NewK8sCrdStorageAddonDbAccess 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewK8sCrdStorageAddonDbAccess(db *gorm.DB) K8sCrdStorageAddonDbAccess {
	return &K8sCrdStorageAddonDbAccessImpl{db: db}
}
