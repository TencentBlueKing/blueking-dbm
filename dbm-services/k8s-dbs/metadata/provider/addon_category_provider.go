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
	entitys "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// AddonCategoryProvider 定义 operation definition 业务逻辑层访问接口
type AddonCategoryProvider interface {
	Create(entity *entitys.AddonCategoryEntity) (*entitys.AddonCategoryEntity, error)
	FindByID(id uint64) (*entitys.AddonCategoryEntity, error)
	ListByLimit(limit int) ([]*entitys.AddonCategoryTypesEntity, error)
}

// AddonCategoryProviderImpl AddonCategoryProvider 具体实现
type AddonCategoryProviderImpl struct {
	categoryDbAccess dbaccess.AddonCategoryDbAccess
	typeDbAccess     dbaccess.AddonTypeDbAccess
}

// FindByID 按照 ID 查找接口实现
func (a *AddonCategoryProviderImpl) FindByID(id uint64) (*entitys.AddonCategoryEntity, error) {
	model, err := a.categoryDbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon category with id %d", id)
	}
	categoryEntity := &entitys.AddonCategoryEntity{}
	if err := copier.Copy(categoryEntity, model); err != nil {
		return nil, err
	}
	return categoryEntity, nil
}

// Create 创建 addon category
func (a *AddonCategoryProviderImpl) Create(entity *entitys.AddonCategoryEntity) (
	*entitys.AddonCategoryEntity, error,
) {
	model := models.AddonCategoryModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	addedModel, err := a.categoryDbAccess.Create(&model)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addon category with entity %+v", entity)
	}
	addedEntity := entitys.AddonCategoryEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &addedEntity, nil
}

// ListByLimit 获取 addon category 列表
func (a *AddonCategoryProviderImpl) ListByLimit(limit int) (
	[]*entitys.AddonCategoryTypesEntity,
	error,
) {
	categoryModels, err := a.categoryDbAccess.ListByLimit(limit)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list addon category with limit %d", limit)
	}
	var categoryEntities []*entitys.AddonCategoryTypesEntity
	if err = copier.Copy(&categoryEntities, categoryModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	for i, category := range categoryEntities {
		addonTypeModels, err := a.typeDbAccess.FindByCategoryID(category.ID)
		if err != nil {
			return nil, errors.Wrapf(err, "failed to list addon type with categoryID %d", category.ID)
		}
		var addonTypeEntities []*entitys.AddonTypeEntity
		if err := copier.Copy(&addonTypeEntities, addonTypeModels); err != nil {
			return nil, errors.Wrap(err, "failed to copy")
		}
		categoryEntities[i].AddonTypes = addonTypeEntities
	}

	return categoryEntities, nil
}

// NewAddonCategoryProvider 创建 AddonCategoryProvider 接口实现实例
func NewAddonCategoryProvider(
	categoryDbAccess dbaccess.AddonCategoryDbAccess,
	typeDbAccess dbaccess.AddonTypeDbAccess,
) AddonCategoryProvider {
	return &AddonCategoryProviderImpl{categoryDbAccess: categoryDbAccess, typeDbAccess: typeDbAccess}
}
