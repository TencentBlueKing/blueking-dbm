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

// AddonSpecPlanProvider 定义 addon 套餐配置业务辑层访问接口
type AddonSpecPlanProvider interface {
	CreateSpecPlan(dbsCtx *commentity.DbsContext, model *metaentity.AddonSpecPlanEntity) (
		*metaentity.AddonSpecPlanEntity, error)
	DeleteSpecPlanByID(id uint64) (uint64, error)
	FindSpecPlanByID(id uint64) (*metaentity.AddonSpecPlanEntity, error)
	FindSpecPlanByParams(params *metaentity.AddonSpecPlanQueryParams) ([]*metaentity.AddonSpecPlanEntity, error)
	UpdateSpecPlan(dbsCtx *commentity.DbsContext, model *metaentity.AddonSpecPlanEntity) (uint64, error)
}

// AddonSpecPlanProviderImpl AddonSpecPlanProvider 具体实现
type AddonSpecPlanProviderImpl struct {
	dbAccess dbaccess.AddonSpecPlanDbAccess
}

var (
	addonSpecPlanInstance AddonSpecPlanProvider
	addonSpecPlanOnce     sync.Once
)

// GetAddonSpecPlanProvider 获取 AddonSpecPlanProvider 单例实例
func GetAddonSpecPlanProvider(dbAccess dbaccess.AddonSpecPlanDbAccess) AddonSpecPlanProvider {
	addonSpecPlanOnce.Do(func() {
		addonSpecPlanInstance = &AddonSpecPlanProviderImpl{dbAccess: dbAccess}
	})
	if addonSpecPlanInstance == nil {
		panic("AddonSpecPlanProvider instance is nil after initialization")
	}
	return addonSpecPlanInstance
}

// CreateSpecPlan 创建 addon spec plan
func (a *AddonSpecPlanProviderImpl) CreateSpecPlan(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.AddonSpecPlanEntity,
) (*metaentity.AddonSpecPlanEntity, error) {
	specPlanModel := metamodel.AddonSpecPlanModel{}
	entity.CreatedBy = dbsCtx.BkAuth.BkUserName
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName

	if err := copier.Copy(&specPlanModel, entity); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	addedSpecPlanModel, err := a.dbAccess.Create(&specPlanModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addon spec plan with entity: %+v", entity)
	}

	specPlanEntity := metaentity.AddonSpecPlanEntity{}
	if err = copier.Copy(&specPlanEntity, addedSpecPlanModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	return &specPlanEntity, nil
}

// DeleteSpecPlanByID 删除 addon spec plan
func (a *AddonSpecPlanProviderImpl) DeleteSpecPlanByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindSpecPlanByID 按照 ID 查询 addon spec plan
func (a *AddonSpecPlanProviderImpl) FindSpecPlanByID(id uint64) (*metaentity.AddonSpecPlanEntity, error) {
	specPlanModel, err := a.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon spec plan with id %d", id)
	}
	specPlanEntity := metaentity.AddonSpecPlanEntity{}
	if err = copier.Copy(&specPlanEntity, specPlanModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return &specPlanEntity, nil
}

// FindSpecPlanByParams 按照参数查询 addon spec plan
func (a *AddonSpecPlanProviderImpl) FindSpecPlanByParams(
	params *metaentity.AddonSpecPlanQueryParams,
) (
	[]*metaentity.AddonSpecPlanEntity,
	error,
) {
	specPlanModels, err := a.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon spec plan with params %+v", params)
	}
	var specPlanEntities []*metaentity.AddonSpecPlanEntity
	if err = copier.Copy(&specPlanEntities, specPlanModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return specPlanEntities, nil
}

// UpdateSpecPlan 更新 addon spec plan
func (a *AddonSpecPlanProviderImpl) UpdateSpecPlan(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.AddonSpecPlanEntity,
) (uint64, error) {
	specPlanModel := metamodel.AddonSpecPlanModel{}
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName
	if err := copier.Copy(&specPlanModel, entity); err != nil {
		return 0, errors.Wrapf(err, "failed to copy")
	}

	rows, err := a.dbAccess.Update(&specPlanModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addon spec plan with entity: %+v", entity)
	}
	return rows, nil
}
