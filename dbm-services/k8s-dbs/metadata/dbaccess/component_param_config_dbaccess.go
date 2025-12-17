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
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// AddonParamConfigDbAccess 定义组件参数配置的数据库访问接口
type AddonParamConfigDbAccess interface {
	// FindByParams 根据条件查询参数配置
	FindByParams(params *metaentity.AddonParamConfigQueryParams) ([]*metamodel.AddonParamConfigModel, error)
	// Create 创建单条记录
	Create(model *metamodel.AddonParamConfigModel) (*metamodel.AddonParamConfigModel, error)
	// BatchCreate 批量创建
	BatchCreate(models []*metamodel.AddonParamConfigModel) error
	// DeleteByID 根据 ID 删除
	DeleteByID(id uint64) (uint64, error)
	// Update 更新记录
	Update(model *metamodel.AddonParamConfigModel) (uint64, error)
}

// AddonParamConfigDbAccessImpl AddonParamConfigDbAccess 的具体实现
type AddonParamConfigDbAccessImpl struct {
	db *gorm.DB
}

// FindByParams 根据条件查询参数配置
func (k *AddonParamConfigDbAccessImpl) FindByParams(
	params *metaentity.AddonParamConfigQueryParams,
) ([]*metamodel.AddonParamConfigModel, error) {
	var models []*metamodel.AddonParamConfigModel
	err := k.db.
		Where(params).
		Limit(commconst.MaxFetchSize).
		Find(&models).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find component param config with params %+v", params)
	}
	return models, nil
}

// Create 创建单条记录
func (k *AddonParamConfigDbAccessImpl) Create(
	model *metamodel.AddonParamConfigModel,
) (*metamodel.AddonParamConfigModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create component param config with model %+v", model)
	}
	return model, nil
}

// BatchCreate 批量创建
func (k *AddonParamConfigDbAccessImpl) BatchCreate(
	models []*metamodel.AddonParamConfigModel,
) error {
	if len(models) == 0 {
		return nil
	}
	if err := k.db.Create(models).Error; err != nil {
		return errors.Wrapf(err, "failed to batch create component param configs")
	}
	return nil
}

// DeleteByID 根据 ID 删除
func (k *AddonParamConfigDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&metamodel.AddonParamConfigModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete component param config with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// Update 更新记录
func (k *AddonParamConfigDbAccessImpl) Update(
	model *metamodel.AddonParamConfigModel,
) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update component param config with model %+v", model)
	}
	return uint64(result.RowsAffected), nil
}

// NewAddonParamConfigDbAccess 创建 AddonParamConfigDbAccess 接口实现实例
func NewAddonParamConfigDbAccess(db *gorm.DB) AddonParamConfigDbAccess {
	return &AddonParamConfigDbAccessImpl{db: db}
}
