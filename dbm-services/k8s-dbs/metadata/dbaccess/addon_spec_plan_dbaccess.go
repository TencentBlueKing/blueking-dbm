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
	"sync"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// AddonSpecPlanDbAccess 定义 addon spec plan 元数据的数据库访问接口
type AddonSpecPlanDbAccess interface {
	Create(model *metamodel.AddonSpecPlanModel) (*metamodel.AddonSpecPlanModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.AddonSpecPlanModel, error)
	FindByParams(params *metaentity.AddonSpecPlanQueryParams) ([]*metamodel.AddonSpecPlanModel, error)
	Update(model *metamodel.AddonSpecPlanModel) (uint64, error)
}

// AddonSpecPlanDbAccessImpl AddonSpecPlanDbAccess 的具体实现
type AddonSpecPlanDbAccessImpl struct {
	db *gorm.DB
}

var (
	addonSpecPlanInstance AddonSpecPlanDbAccess
	addonSpecPlanOnce     sync.Once
)

// GetAddonSpecPlanDbAccess 获取 AddonSpecPlanDbAccess 单例实例
func GetAddonSpecPlanDbAccess(db *gorm.DB) AddonSpecPlanDbAccess {
	addonSpecPlanOnce.Do(func() {
		addonSpecPlanInstance = &AddonSpecPlanDbAccessImpl{db: db}
	})
	if addonSpecPlanInstance == nil {
		panic("AddonSpecPlanDbAccess instance is nil after initialization")
	}
	return addonSpecPlanInstance
}

// Create 创建 addon spec plan 元数据接口实现
func (a *AddonSpecPlanDbAccessImpl) Create(model *metamodel.AddonSpecPlanModel) (
	*metamodel.AddonSpecPlanModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create addon spec plan with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除 addon spec plan 元数据接口实现
func (a *AddonSpecPlanDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := a.db.Where("active = 1").Delete(&metamodel.AddonSpecPlanModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete addon spec plan with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 addon spec plan 元数据接口实现
func (a *AddonSpecPlanDbAccessImpl) FindByID(id uint64) (*metamodel.AddonSpecPlanModel, error) {
	var model metamodel.AddonSpecPlanModel
	result := a.db.Where("active = 1").First(&model, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find addon spec plan with id %d", id)
	}
	return &model, nil
}

// FindByParams 参数查询实现
func (a *AddonSpecPlanDbAccessImpl) FindByParams(params *metaentity.AddonSpecPlanQueryParams) (
	[]*metamodel.AddonSpecPlanModel,
	error,
) {
	var models []*metamodel.AddonSpecPlanModel
	query := a.db.Where("active = 1")

	if params.ID > 0 {
		query = query.Where("id = ?", params.ID)
	}
	if params.AddonID > 0 {
		query = query.Where("addon_id = ?", params.AddonID)
	}
	if params.AddonTopology != "" {
		query = query.Where("addon_topology = ?", params.AddonTopology)
	}
	if params.SpecLevel != "" {
		query = query.Where("spec_level = ?", params.SpecLevel)
	}

	err := query.Limit(commconst.MaxFetchSize).Find(&models).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon spec plan with params %+v", params)
	}
	return models, nil
}

// Update 更新 addon spec plan 元数据接口实现
func (a *AddonSpecPlanDbAccessImpl) Update(model *metamodel.AddonSpecPlanModel) (uint64, error) {
	result := a.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update addon spec plan with model %+v", model)
	}
	return uint64(result.RowsAffected), nil
}
