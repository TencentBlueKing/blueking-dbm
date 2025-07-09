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
	commentity "k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// AddonHelmRepoDbAccess 定义 AddonClusterHelmRepo 元数据的数据库访问接口
type AddonHelmRepoDbAccess interface {
	Create(model *metamodel.AddonHelmRepoModel) (*metamodel.AddonHelmRepoModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.AddonHelmRepoModel, error)
	FindByParams(params *metaentity.HelmRepoQueryParams) (*metamodel.AddonHelmRepoModel, error)
	Update(model *metamodel.AddonHelmRepoModel) (uint64, error)
	ListByPage(pagination commentity.Pagination) ([]metamodel.AddonHelmRepoModel, int64, error)
}

// AddonHelmRepoDbAccessImpl AddonHelmRepoDbAccess 的具体实现
type AddonHelmRepoDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建接口实现
func (a *AddonHelmRepoDbAccessImpl) Create(model *metamodel.AddonHelmRepoModel) (
	*metamodel.AddonHelmRepoModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	return model, nil
}

// DeleteByID 删除接口实现
func (a *AddonHelmRepoDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := a.db.Delete(&metamodel.AddonHelmRepoModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找接口实现
func (a *AddonHelmRepoDbAccessImpl) FindByID(id uint64) (*metamodel.AddonHelmRepoModel, error) {
	var model metamodel.AddonHelmRepoModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &model, nil
}

// FindByParams 根据参数查找接口实现
func (a *AddonHelmRepoDbAccessImpl) FindByParams(params *metaentity.HelmRepoQueryParams) (
	*metamodel.AddonHelmRepoModel,
	error,
) {
	var helmRepo metamodel.AddonHelmRepoModel
	result := a.db.Where(params).First(&helmRepo)
	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}

	return &helmRepo, nil
}

// Update 更新接口实现
func (a *AddonHelmRepoDbAccessImpl) Update(model *metamodel.AddonHelmRepoModel) (uint64, error) {
	result := a.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询接口实现
func (a *AddonHelmRepoDbAccessImpl) ListByPage(pagination commentity.Pagination) (
	[]metamodel.AddonHelmRepoModel,
	int64,
	error,
) {
	var releaseModels []metamodel.AddonHelmRepoModel
	if err := a.db.Offset(pagination.Page).Limit(pagination.Limit).Find(&releaseModels).Error; err != nil {
		slog.Error("List model error", "error", err.Error())
		return nil, 0, err
	}
	return releaseModels, int64(len(releaseModels)), nil
}

// NewAddonHelmRepoDbAccess 创建 AddonHelmRepoDbAccess 接口实现实例
func NewAddonHelmRepoDbAccess(db *gorm.DB) AddonHelmRepoDbAccess {
	return &AddonHelmRepoDbAccessImpl{db: db}
}
