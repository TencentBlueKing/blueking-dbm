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
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// K8sCrdStorageAddonDbAccess 定义 addon 元数据的数据库访问接口
type K8sCrdStorageAddonDbAccess interface {
	Create(model *metamodel.K8sCrdStorageAddonModel) (*metamodel.K8sCrdStorageAddonModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.K8sCrdStorageAddonModel, error)
	FindByParams(params *metaentity.AddonQueryParams) ([]*metamodel.K8sCrdStorageAddonModel, error)
	Update(model *metamodel.K8sCrdStorageAddonModel) (uint64, error)
	ListByPage(pagination commentity.Pagination) ([]metamodel.K8sCrdStorageAddonModel, int64, error)
	FindVersionsByParams(params *metaentity.AddonVersionQueryParams) ([]*metamodel.AddonVersionModel, error)
}

// K8sCrdStorageAddonDbAccessImpl K8sCrdStorageAddonDbAccess 的具体实现
type K8sCrdStorageAddonDbAccessImpl struct {
	db *gorm.DB
}

// FindVersionsByParams 查询 addon 版本信息
func (k *K8sCrdStorageAddonDbAccessImpl) FindVersionsByParams(params *metaentity.AddonVersionQueryParams) (
	[]*metamodel.AddonVersionModel,
	error,
) {
	var versions []*metamodel.AddonVersionModel
	if err := k.db.Debug().Model(&metamodel.K8sCrdStorageAddonModel{}).
		Where(params).
		Find(&versions).
		Limit(commconst.MaxFetchSize).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to list addon versions with params %+v", params)
	}
	return versions, nil
}

// FindByParams 参数查询实现
func (k *K8sCrdStorageAddonDbAccessImpl) FindByParams(params *metaentity.AddonQueryParams) (
	[]*metamodel.K8sCrdStorageAddonModel,
	error,
) {
	var addonModels []*metamodel.K8sCrdStorageAddonModel
	err := k.db.
		Where(params).
		Limit(commconst.MaxFetchSize).
		Find(&addonModels).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with params %+v", params)
	}
	return addonModels, nil
}

// Create 创建 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) Create(model *metamodel.K8sCrdStorageAddonModel) (
	*metamodel.K8sCrdStorageAddonModel,
	error,
) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create addon with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&metamodel.K8sCrdStorageAddonModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete addon with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) FindByID(id uint64) (*metamodel.K8sCrdStorageAddonModel, error) {
	var addonModel metamodel.K8sCrdStorageAddonModel
	result := k.db.First(&addonModel, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find addon with id %d", id)
	}
	return &addonModel, nil
}

// Update 更新 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) Update(storageAddonModel *metamodel.K8sCrdStorageAddonModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(storageAddonModel)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update addon with model %+v", storageAddonModel)
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 addon 元数据接口实现
func (k *K8sCrdStorageAddonDbAccessImpl) ListByPage(pagination commentity.Pagination) (
	[]metamodel.K8sCrdStorageAddonModel,
	int64,
	error,
) {
	var addonModel []metamodel.K8sCrdStorageAddonModel
	if err := k.db.Offset(pagination.Page).Limit(pagination.Limit).Where("active=1").Find(&addonModel).Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to list addons with pagination %+v", pagination)
	}
	return addonModel, int64(len(addonModel)), nil
}

// NewK8sCrdStorageAddonDbAccess 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewK8sCrdStorageAddonDbAccess(db *gorm.DB) K8sCrdStorageAddonDbAccess {
	return &K8sCrdStorageAddonDbAccessImpl{db}
}
