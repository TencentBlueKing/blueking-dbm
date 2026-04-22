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

// ComponentSpecPlanDbAccess 定义 component spec plan 元数据的数据库访问接口
type ComponentSpecPlanDbAccess interface {
	Create(model *metamodel.ComponentSpecPlanModel) (*metamodel.ComponentSpecPlanModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.ComponentSpecPlanModel, error)
	FindByParams(params *metaentity.ComponentSpecPlanQueryParams) ([]*metamodel.ComponentSpecPlanModel, error)
	Update(model *metamodel.ComponentSpecPlanModel) (uint64, error)
}

// ComponentSpecPlanDbAccessImpl ComponentSpecPlanDbAccess 的具体实现
type ComponentSpecPlanDbAccessImpl struct {
	db *gorm.DB
}

var (
	componentSpecPlanInstance ComponentSpecPlanDbAccess
	componentSpecPlanOnce     sync.Once
)

// GetComponentSpecPlanDbAccess 获取 ComponentSpecPlanDbAccess 单例实例
func GetComponentSpecPlanDbAccess(db *gorm.DB) ComponentSpecPlanDbAccess {
	componentSpecPlanOnce.Do(func() {
		componentSpecPlanInstance = &ComponentSpecPlanDbAccessImpl{db: db}
	})
	if componentSpecPlanInstance == nil {
		panic("ComponentSpecPlanDbAccess instance is nil after initialization")
	}
	return componentSpecPlanInstance
}

// Create 创建 component spec plan 元数据接口实现
func (c *ComponentSpecPlanDbAccessImpl) Create(model *metamodel.ComponentSpecPlanModel) (
	*metamodel.ComponentSpecPlanModel,
	error,
) {
	if err := c.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create component spec plan with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除 component spec plan 元数据接口实现
func (c *ComponentSpecPlanDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := c.db.Where("active = 1").Delete(&metamodel.ComponentSpecPlanModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete component spec plan with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 component spec plan 元数据接口实现
func (c *ComponentSpecPlanDbAccessImpl) FindByID(id uint64) (*metamodel.ComponentSpecPlanModel, error) {
	var model metamodel.ComponentSpecPlanModel
	result := c.db.Where("active = 1").First(&model, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find component spec plan with id %d", id)
	}
	return &model, nil
}

// FindByParams 参数查询实现
func (c *ComponentSpecPlanDbAccessImpl) FindByParams(params *metaentity.ComponentSpecPlanQueryParams) (
	[]*metamodel.ComponentSpecPlanModel,
	error,
) {
	var models []*metamodel.ComponentSpecPlanModel
	query := c.db.Where("active = 1")

	if params.ID > 0 {
		query = query.Where("id = ?", params.ID)
	}
	if params.AddonSpecPlanID > 0 {
		query = query.Where("addon_spec_plan_id = ?", params.AddonSpecPlanID)
	}
	if params.ComponentName != "" {
		query = query.Where("component_name = ?", params.ComponentName)
	}

	err := query.Limit(commconst.MaxFetchSize).Find(&models).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find component spec plan with params %+v", params)
	}
	return models, nil
}

// Update 更新 component spec plan 元数据接口实现
func (c *ComponentSpecPlanDbAccessImpl) Update(model *metamodel.ComponentSpecPlanModel) (uint64, error) {
	result := c.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update component spec plan with model %+v", model)
	}
	return uint64(result.RowsAffected), nil
}
