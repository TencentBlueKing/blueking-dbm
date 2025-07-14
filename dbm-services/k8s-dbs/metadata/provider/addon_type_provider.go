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
	"log/slog"

	"github.com/jinzhu/copier"
)

// AddonTypeProvider 定义 operation definition 业务逻辑层访问接口
type AddonTypeProvider interface {
	Create(entity *entitys.AddonTypeEntity) (*entitys.AddonTypeEntity, error)
	ListByLimit(limit int) ([]*entitys.AddonTypeEntity, error)
}

// AddonTypeProviderImpl AddonTypeProvider 具体实现
type AddonTypeProviderImpl struct {
	typeDbAccess     dbaccess.AddonTypeDbAccess
	categoryDbAccess dbaccess.AddonCategoryDbAccess
}

// Create 创建 addon type
func (a *AddonTypeProviderImpl) Create(entity *entitys.AddonTypeEntity) (
	*entitys.AddonTypeEntity, error,
) {
	model := models.AddonTypeModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := a.typeDbAccess.Create(&model)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.AddonTypeEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// ListByLimit 获取 addon type 列表
func (a *AddonTypeProviderImpl) ListByLimit(limit int) (
	[]*entitys.AddonTypeEntity,
	error,
) {
	typeModels, err := a.typeDbAccess.ListByLimit(limit)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	var typeEntities []*entitys.AddonTypeEntity
	if err := copier.Copy(&typeEntities, typeModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}

	for i, typeEntity := range typeEntities {
		categoryModel, err := a.categoryDbAccess.FindByID(typeEntity.CategoryID)
		if err != nil {
			return nil, err
		}
		categoryEntity := &entitys.AddonCategoryEntity{}
		if err := copier.Copy(categoryEntity, categoryModel); err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		}
		typeEntities[i].AddonCategory = categoryEntity
	}

	return typeEntities, nil
}

// NewAddonTypeProvider 创建 AddonTypeProvider 接口实现实例
func NewAddonTypeProvider(
	typeDbAccess dbaccess.AddonTypeDbAccess,
	categoryDbAccess dbaccess.AddonCategoryDbAccess,
) AddonTypeProvider {
	return &AddonTypeProviderImpl{typeDbAccess: typeDbAccess, categoryDbAccess: categoryDbAccess}
}
