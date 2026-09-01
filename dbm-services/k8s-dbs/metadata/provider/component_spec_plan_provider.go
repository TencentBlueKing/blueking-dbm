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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/metadata/dbaccess"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"
	"sync"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// ComponentSpecPlanProvider 定义 addon 关联的 component 套餐配置业务辑层访问接口
type ComponentSpecPlanProvider interface {
	CreateSpecPlan(dbsCtx *commentity.DbsContext, model *metaentity.ComponentSpecPlanEntity) (
		*metaentity.ComponentSpecPlanEntity, error)
	DeleteSpecPlanByID(id uint64) (uint64, error)
	FindSpecPlanByID(id uint64) (*metaentity.ComponentSpecPlanEntity, error)
	FindSpecPlanByParams(params *metaentity.ComponentSpecPlanQueryParams) ([]*metaentity.ComponentSpecPlanEntity, error)
	UpdateSpecPlan(dbsCtx *commentity.DbsContext, model *metaentity.ComponentSpecPlanEntity) (uint64, error)
}

// ComponentSpecPlanProviderImpl ComponentSpecPlanProvider 具体实现
type ComponentSpecPlanProviderImpl struct {
	dbAccess dbaccess.ComponentSpecPlanDbAccess
}

var (
	componentSpecPlanInstance ComponentSpecPlanProvider
	componentSpecPlanOnce     sync.Once
)

// GetComponentSpecPlanProvider 获取 ComponentSpecPlanProvider 单例实例
func GetComponentSpecPlanProvider(dbAccess dbaccess.ComponentSpecPlanDbAccess) ComponentSpecPlanProvider {
	componentSpecPlanOnce.Do(func() {
		componentSpecPlanInstance = &ComponentSpecPlanProviderImpl{dbAccess: dbAccess}
	})
	if componentSpecPlanInstance == nil {
		panic("ComponentSpecPlanProvider instance is nil after initialization")
	}
	return componentSpecPlanInstance
}

// CreateSpecPlan 创建 component spec plan
func (c *ComponentSpecPlanProviderImpl) CreateSpecPlan(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.ComponentSpecPlanEntity,
) (*metaentity.ComponentSpecPlanEntity, error) {
	specPlanModel := metamodel.ComponentSpecPlanModel{}
	entity.CreatedBy = dbsCtx.BkAdditional.BkUserName
	entity.UpdatedBy = dbsCtx.BkAdditional.BkUserName

	if err := copier.Copy(&specPlanModel, entity); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	addedSpecPlanModel, err := c.dbAccess.Create(&specPlanModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create component spec plan with entity: %+v", entity)
	}

	specPlanEntity := metaentity.ComponentSpecPlanEntity{}
	if err = copier.Copy(&specPlanEntity, addedSpecPlanModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	return &specPlanEntity, nil
}

// DeleteSpecPlanByID 删除 component spec plan
func (c *ComponentSpecPlanProviderImpl) DeleteSpecPlanByID(id uint64) (uint64, error) {
	return c.dbAccess.DeleteByID(id)
}

// FindSpecPlanByID 按照 ID 查询 component spec plan
func (c *ComponentSpecPlanProviderImpl) FindSpecPlanByID(id uint64) (*metaentity.ComponentSpecPlanEntity, error) {
	specPlanModel, err := c.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find component spec plan with id %d", id)
	}
	specPlanEntity := metaentity.ComponentSpecPlanEntity{}
	if err = copier.Copy(&specPlanEntity, specPlanModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return &specPlanEntity, nil
}

// FindSpecPlanByParams 按照参数查询 component spec plan
func (c *ComponentSpecPlanProviderImpl) FindSpecPlanByParams(params *metaentity.ComponentSpecPlanQueryParams) (
	[]*metaentity.ComponentSpecPlanEntity,
	error,
) {
	specPlanModels, err := c.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find component spec plan with params %+v", params)
	}
	var specPlanEntities []*metaentity.ComponentSpecPlanEntity
	if err = copier.Copy(&specPlanEntities, specPlanModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return specPlanEntities, nil
}

// UpdateSpecPlan 更新 component spec plan
func (c *ComponentSpecPlanProviderImpl) UpdateSpecPlan(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.ComponentSpecPlanEntity,
) (uint64, error) {
	specPlanModel := metamodel.ComponentSpecPlanModel{}
	entity.UpdatedBy = dbsCtx.BkAdditional.BkUserName
	if err := copier.Copy(&specPlanModel, entity); err != nil {
		return 0, errors.Wrapf(err, "failed to copy")
	}

	rows, err := c.dbAccess.Update(&specPlanModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update component spec plan with entity: %+v", entity)
	}
	return rows, nil
}
