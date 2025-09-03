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

// AddonTopologyDbAccess 定义 addon topology 元数据的数据库访问接口
type AddonTopologyDbAccess interface {
	Create(model *metamodel.AddonTopologyModel) (*metamodel.AddonTopologyModel, error)
	FindByID(id uint64) (*metamodel.AddonTopologyModel, error)
	FindByParams(params *metaentity.AddonTopologyQueryParams) ([]*metamodel.AddonTopologyModel, error)
	ListByLimit(limit int) ([]*metamodel.AddonTopologyModel, error)
}

// AddonTopologyDbAccessImpl AddonCategoryDbAccess 的具体实现
type AddonTopologyDbAccessImpl struct {
	db *gorm.DB
}

// FindByParams 按照参数查找
func (a *AddonTopologyDbAccessImpl) FindByParams(params *metaentity.AddonTopologyQueryParams) (
	[]*metamodel.AddonTopologyModel,
	error,
) {
	var topoModels []*metamodel.AddonTopologyModel
	err := a.db.Debug().Where(params).Limit(commconst.MaxFetchSize).Find(&topoModels).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon topologies with params %+v", params)
	}
	return topoModels, nil
}

// FindByID 按照 ID 查找接口实现
func (a *AddonTopologyDbAccessImpl) FindByID(id uint64) (*metamodel.AddonTopologyModel, error) {
	var model metamodel.AddonTopologyModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find addon topology with id %v", id)
	}
	return &model, nil
}

// ListByLimit limit 查询实现
func (a *AddonTopologyDbAccessImpl) ListByLimit(limit int) ([]*metamodel.AddonTopologyModel, error) {
	var cmpOpsDefModels []*metamodel.AddonTopologyModel
	if err := a.db.Limit(limit).Where("active=1").Find(&cmpOpsDefModels).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to list addon topologies with limit %v", limit)
	}
	return cmpOpsDefModels, nil
}

// Create 创建接口实现
func (a *AddonTopologyDbAccessImpl) Create(model *metamodel.AddonTopologyModel) (
	*metamodel.AddonTopologyModel,
	error,
) {
	if err := a.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create addon topology with model %+v", model)
	}
	return model, nil
}

// NewAddonTopologyDbAccess 创建 AddonTopologyDbAccess 接口实现实例
func NewAddonTopologyDbAccess(db *gorm.DB) AddonTopologyDbAccess {
	return &AddonTopologyDbAccessImpl{db: db}
}
