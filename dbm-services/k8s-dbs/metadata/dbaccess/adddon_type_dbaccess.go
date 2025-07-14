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
	models "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// AddonTypeDbAccess 定义 component operation 元数据的数据库访问接口
type AddonTypeDbAccess interface {
	Create(model *models.AddonTypeModel) (*models.AddonTypeModel, error)
	FindByID(id uint64) (*models.AddonTypeModel, error)
	FindByCategoryID(id uint64) ([]*models.AddonTypeModel, error)
	ListByLimit(limit int) ([]*models.AddonTypeModel, error)
}

// AddonTypeDbAccessImpl AddonTypeDbAccess 的具体实现
type AddonTypeDbAccessImpl struct {
	db *gorm.DB
}

// FindByCategoryID 按照 category id 查找接口实现
func (a *AddonTypeDbAccessImpl) FindByCategoryID(id uint64) ([]*models.AddonTypeModel, error) {
	var typeModels []*models.AddonTypeModel
	if err := a.db.Where("category_id = ?", id).Find(&typeModels).Error; err != nil {
		return nil, err
	}
	return typeModels, nil
}

// FindByID 按照 ID 查找接口实现
func (a *AddonTypeDbAccessImpl) FindByID(id uint64) (*models.AddonTypeModel, error) {
	var model *models.AddonTypeModel
	result := a.db.First(model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return model, nil
}

// ListByLimit limit 查询实现
func (a *AddonTypeDbAccessImpl) ListByLimit(limit int) ([]*models.AddonTypeModel, error) {
	var cmpOpsDefModels []*models.AddonTypeModel
	if err := a.db.
		Limit(limit).
		Where("active=1").Find(&cmpOpsDefModels).Error; err != nil {
		slog.Error("List by limit error", "error", err)
		return nil, err
	}
	return cmpOpsDefModels, nil
}

// Create 创建接口实现
func (a *AddonTypeDbAccessImpl) Create(model *models.AddonTypeModel) (
	*models.AddonTypeModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	return model, nil
}

// NewAddonTypeDbAccess 创建 AddonTypeDbAccess 接口实现实例
func NewAddonTypeDbAccess(db *gorm.DB) AddonTypeDbAccess {
	return &AddonTypeDbAccessImpl{db: db}
}
