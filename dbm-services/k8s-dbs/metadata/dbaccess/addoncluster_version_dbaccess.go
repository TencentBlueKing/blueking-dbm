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
	mconst "k8s-dbs/common/constant"
	"k8s-dbs/common/entity"
	models "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"gorm.io/gorm"
)

// AddonClusterVersionDbAccess 定义 addon cluster version 元数据的数据库访问接口
type AddonClusterVersionDbAccess interface {
	Create(model *models.AddonClusterVersionModel) (*models.AddonClusterVersionModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.AddonClusterVersionModel, error)
	FindByParams(params map[string]interface{}) ([]*models.AddonClusterVersionModel, error)
	Update(model *models.AddonClusterVersionModel) (uint64, error)
	ListByPage(pagination entity.Pagination) ([]*models.AddonClusterVersionModel, int64, error)
}

// AddonClusterVersionDbAccessImpl AddonClusterVersionDbAccess 的具体实现
type AddonClusterVersionDbAccessImpl struct {
	db *gorm.DB
}

// FindByParams 参数查询实现
func (k *AddonClusterVersionDbAccessImpl) FindByParams(params map[string]interface{}) (
	[]*models.AddonClusterVersionModel,
	error,
) {
	var saModels []*models.AddonClusterVersionModel
	if err := k.db.
		Where(params).
		Limit(mconst.MaxFetchSize).
		Find(&saModels).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, errors.Wrapf(err, "failed to find addon cluster version with params %+v", params)
	}
	return saModels, nil
}

// Create 创建元数据接口实现
func (k *AddonClusterVersionDbAccessImpl) Create(model *models.AddonClusterVersionModel) (
	*models.AddonClusterVersionModel,
	error,
) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to add addon cluster version with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除元数据接口实现
func (k *AddonClusterVersionDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.AddonClusterVersionModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete addon cluster version with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *AddonClusterVersionDbAccessImpl) FindByID(id uint64) (*models.AddonClusterVersionModel, error) {
	var storageAddonModel models.AddonClusterVersionModel
	result := k.db.First(&storageAddonModel, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find addon cluster version with id %d", id)
	}
	return &storageAddonModel, nil
}

// Update 更新元数据接口实现
func (k *AddonClusterVersionDbAccessImpl) Update(storageAddonModel *models.AddonClusterVersionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(storageAddonModel)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update addon cluster version with id %d", storageAddonModel.ID)
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 addon 元数据接口实现
func (k *AddonClusterVersionDbAccessImpl) ListByPage(pagination entity.Pagination) (
	[]*models.AddonClusterVersionModel,
	int64,
	error,
) {
	var addonModels []*models.AddonClusterVersionModel
	if err := k.db.Offset(pagination.Page).Limit(pagination.Limit).Where("active=1").Find(&addonModels).Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to list addon cluster version with pagination %+v", pagination)
	}
	return addonModels, int64(len(addonModels)), nil
}

// NewAddonClusterVersionDbAccess 创建 AddonClusterVersionDbAccess 接口实现实例
func NewAddonClusterVersionDbAccess(db *gorm.DB) AddonClusterVersionDbAccess {
	return &AddonClusterVersionDbAccessImpl{db}
}
