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

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// AddonCategoryDbAccess 定义 component operation 元数据的数据库访问接口
type AddonCategoryDbAccess interface {
	Create(model *models.AddonCategoryModel) (*models.AddonCategoryModel, error)
	FindByID(id uint64) (*models.AddonCategoryModel, error)
	ListByLimit(limit int) ([]*models.AddonCategoryModel, error)
}

// AddonCategoryDbAccessImpl AddonCategoryDbAccess 的具体实现
type AddonCategoryDbAccessImpl struct {
	db *gorm.DB
}

// FindByID 按照 ID 查找接口实现
func (a *AddonCategoryDbAccessImpl) FindByID(id uint64) (*models.AddonCategoryModel, error) {
	var model models.AddonCategoryModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find addon category with id %d", id)
	}
	return &model, nil
}

// ListByLimit limit 查询实现
func (a *AddonCategoryDbAccessImpl) ListByLimit(limit int) ([]*models.AddonCategoryModel, error) {
	var activeAddonCategories []*models.AddonCategoryModel
	if err := a.db.Limit(limit).Where("active = 1").Find(&activeAddonCategories).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to list addon category with limit %d", limit)
	}
	return activeAddonCategories, nil
}

// Create 创建接口实现
func (a *AddonCategoryDbAccessImpl) Create(model *models.AddonCategoryModel) (
	*models.AddonCategoryModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create addon category with model %+v", model)
	}
	return model, nil
}

// NewAddonCategoryDbAccess 创建 AddonCategoryDbAccess 接口实现实例
func NewAddonCategoryDbAccess(db *gorm.DB) AddonCategoryDbAccess {
	return &AddonCategoryDbAccessImpl{db: db}
}
