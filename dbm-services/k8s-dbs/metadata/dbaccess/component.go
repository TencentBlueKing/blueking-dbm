/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use k file except in compliance with the License.

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
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

// K8sCrdComponentDbAccess 定义 component 元数据的数据库访问接口
type K8sCrdComponentDbAccess interface {
	Create(model *models.K8sCrdComponentModel) (*models.K8sCrdComponentModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdComponentModel, error)
	Update(model *models.K8sCrdComponentModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentModel, int64, error)
}

// K8sCrdComponentDbAccessImpl K8sCrdComponentDbAccess 的具体实现
type K8sCrdComponentDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *K8sCrdComponentDbAccessImpl) Create(model *models.K8sCrdComponentModel) (*models.K8sCrdComponentModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	var addedComponent models.K8sCrdComponentModel
	if err := k.db.First(&addedComponent, "id=?", model.ID).Error; err != nil {
		slog.Error("Find component error", "error", err)
		return nil, err
	}
	return &addedComponent, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sCrdComponentDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdComponentModel{}, id)
	if result.Error != nil {
		slog.Error("Delete component error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sCrdComponentDbAccessImpl) FindByID(id uint64) (*models.K8sCrdComponentModel, error) {
	var component models.K8sCrdComponentModel
	result := k.db.First(&component, id)
	if result.Error != nil {
		slog.Error("Find component error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &component, nil
}

// Update 更新元数据接口实现
func (k *K8sCrdComponentDbAccessImpl) Update(model *models.K8sCrdComponentModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update component error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sCrdComponentDbAccessImpl) ListByPage(_ utils.Pagination) ([]models.K8sCrdComponentModel, int64, error) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sCrdComponentAccess 创建 K8sCrdComponentAccess 接口实现实例
func NewK8sCrdComponentAccess(db *gorm.DB) K8sCrdComponentDbAccess {
	return &K8sCrdComponentDbAccessImpl{db: db}
}
