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
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

// AddonClusterHelmRepoDbAccess 定义 AddonClusterHelmRepo 元数据的数据库访问接口
type AddonClusterHelmRepoDbAccess interface {
	Create(model *models.AddonClusterHelmRepoModel) (*models.AddonClusterHelmRepoModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.AddonClusterHelmRepoModel, error)
	FindByParams(params map[string]interface{}) (*models.AddonClusterHelmRepoModel, error)
	Update(model *models.AddonClusterHelmRepoModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.AddonClusterHelmRepoModel, int64, error)
}

// AddonClusterHelmRepoDbAccessImpl AddonClusterHelmRepoDbAccess 的具体实现
type AddonClusterHelmRepoDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建接口实现
func (a *AddonClusterHelmRepoDbAccessImpl) Create(model *models.AddonClusterHelmRepoModel) (
	*models.AddonClusterHelmRepoModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	return model, nil
}

// DeleteByID 删除接口实现
func (a *AddonClusterHelmRepoDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := a.db.Delete(&models.AddonClusterHelmRepoModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找接口实现
func (a *AddonClusterHelmRepoDbAccessImpl) FindByID(id uint64) (*models.AddonClusterHelmRepoModel, error) {
	var model models.AddonClusterHelmRepoModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &model, nil
}

// FindByParams 根据参数查找接口实现
func (a *AddonClusterHelmRepoDbAccessImpl) FindByParams(params map[string]interface{}) (
	*models.AddonClusterHelmRepoModel,
	error,
) {
	var helmRepo models.AddonClusterHelmRepoModel

	// 动态条件查询
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
func (a *AddonClusterHelmRepoDbAccessImpl) Update(model *models.AddonClusterHelmRepoModel) (uint64, error) {
	result := a.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询接口实现
func (a *AddonClusterHelmRepoDbAccessImpl) ListByPage(pagination utils.Pagination) (
	[]models.AddonClusterHelmRepoModel,
	int64,
	error,
) {
	var releaseModels []models.AddonClusterHelmRepoModel
	if err := a.db.Offset(pagination.Page).Limit(pagination.Limit).Find(&releaseModels).Error; err != nil {
		slog.Error("List release error", "error", err.Error())
		return nil, 0, err
	}
	return releaseModels, int64(len(releaseModels)), nil
}

// NewAddonClusterHelmRepoDbAccess 创建 AddonClusterHelmRepoDbAccess 接口实现实例
func NewAddonClusterHelmRepoDbAccess(db *gorm.DB) AddonClusterHelmRepoDbAccess {
	return &AddonClusterHelmRepoDbAccessImpl{db: db}
}
