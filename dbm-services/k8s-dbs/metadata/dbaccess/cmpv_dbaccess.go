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

// K8sCrdCmpvDbAccess 定义 cmpv 元数据的数据库访问接口
type K8sCrdCmpvDbAccess interface {
	Create(model *models.K8sCrdComponentVersionModel) (*models.K8sCrdComponentVersionModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdComponentVersionModel, error)
	Update(model *models.K8sCrdComponentVersionModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentVersionModel, int64, error)
}

// K8sCrdComponentVersionDbAccessImpl K8sCrdCmpvDbAccess 的具体实现
type K8sCrdComponentVersionDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *K8sCrdComponentVersionDbAccessImpl) Create(model *models.K8sCrdComponentVersionModel) (
	*models.K8sCrdComponentVersionModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create componentversion error", "error", err)
		return nil, err
	}
	var created models.K8sCrdComponentVersionModel
	if err := k.db.First(&created, "componentversion_name = ?", model.ComponentVersionName).Error; err != nil {
		slog.Error("Find componentversion error", "error", err)
		return nil, err
	}
	return &created, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sCrdComponentVersionDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdComponentVersionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete componentversion error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sCrdComponentVersionDbAccessImpl) FindByID(id uint64) (*models.K8sCrdComponentVersionModel, error) {
	var cmpvModel models.K8sCrdComponentVersionModel
	result := k.db.First(&cmpvModel, id)
	if result.Error != nil {
		slog.Error("Find componentversion error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &cmpvModel, nil
}

// Update 更新元数据接口实现
func (k *K8sCrdComponentVersionDbAccessImpl) Update(cmpvModel *models.K8sCrdComponentVersionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(cmpvModel)
	if result.Error != nil {
		slog.Error("Update componentversion error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sCrdComponentVersionDbAccessImpl) ListByPage(_ utils.Pagination) (
	[]models.K8sCrdComponentVersionModel,
	int64,
	error,
) {
	// TODO implement me
	panic("implement me")
}

// NewK8sCrdCmpvDbAccess 创建 K8sCrdCmpvDbAccess 接口实现实例
func NewK8sCrdCmpvDbAccess(db *gorm.DB) K8sCrdCmpvDbAccess {
	return &K8sCrdComponentVersionDbAccessImpl{db: db}
}
