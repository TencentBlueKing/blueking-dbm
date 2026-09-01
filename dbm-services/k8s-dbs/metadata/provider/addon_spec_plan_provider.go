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
	commconst "k8s-dbs/common/constant"
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
	FindSpecPlanDetails(params *metaentity.AddonSpecPlanDetailQueryParams) (
		[]*metaentity.AddonSpecPlanDetailEntity, error)
}

// AddonSpecPlanProviderImpl AddonSpecPlanProvider 具体实现
type AddonSpecPlanProviderImpl struct {
	dbAccess              dbaccess.AddonSpecPlanDbAccess
	storageAddonDbAccess  dbaccess.K8sCrdStorageAddonDbAccess
	componentSpecDbAccess dbaccess.ComponentSpecPlanDbAccess
}

var (
	addonSpecPlanInstance AddonSpecPlanProvider
	addonSpecPlanOnce     sync.Once
)

// AddonSpecPlanProviderOptions AddonSpecPlanProvider 函数选项
type AddonSpecPlanProviderOptions func(*AddonSpecPlanProviderImpl)

// AddonSpecPlanProviderBuilder 辅助构建结构体
type AddonSpecPlanProviderBuilder struct{}

// WithSpecPlanDbAccess 设置 AddonSpecPlanDbAccess
func (a *AddonSpecPlanProviderBuilder) WithSpecPlanDbAccess(
	access dbaccess.AddonSpecPlanDbAccess,
) AddonSpecPlanProviderOptions {
	return func(p *AddonSpecPlanProviderImpl) {
		p.dbAccess = access
	}
}

// WithStorageAddonDbAccess 设置 K8sCrdStorageAddonDbAccess
func (a *AddonSpecPlanProviderBuilder) WithStorageAddonDbAccess(
	access dbaccess.K8sCrdStorageAddonDbAccess,
) AddonSpecPlanProviderOptions {
	return func(p *AddonSpecPlanProviderImpl) {
		p.storageAddonDbAccess = access
	}
}

// WithComponentSpecPlanDbAccess 设置 ComponentSpecPlanDbAccess
func (a *AddonSpecPlanProviderBuilder) WithComponentSpecPlanDbAccess(
	access dbaccess.ComponentSpecPlanDbAccess,
) AddonSpecPlanProviderOptions {
	return func(p *AddonSpecPlanProviderImpl) {
		p.componentSpecDbAccess = access
	}
}

// GetAddonSpecPlanProvider 获取 AddonSpecPlanProvider 单例实例
func GetAddonSpecPlanProvider(options ...AddonSpecPlanProviderOptions) AddonSpecPlanProvider {
	addonSpecPlanOnce.Do(func() {
		p := &AddonSpecPlanProviderImpl{}
		for _, option := range options {
			option(p)
		}
		if err := p.validateProvider(); err != nil {
			panic(errors.Wrap(err, "validate provider failed"))
		}
		addonSpecPlanInstance = p
	})
	if addonSpecPlanInstance == nil {
		panic("AddonSpecPlanProvider instance is nil after initialization")
	}
	return addonSpecPlanInstance
}

func (a *AddonSpecPlanProviderImpl) validateProvider() error {
	if a.dbAccess == nil {
		return errors.New("addonSpecPlanDbAccess is required")
	}
	if a.storageAddonDbAccess == nil {
		return errors.New("storageAddonDbAccess is required")
	}
	if a.componentSpecDbAccess == nil {
		return errors.New("componentSpecPlanDbAccess is required")
	}
	return nil
}

// CreateSpecPlan 创建 addon spec plan
func (a *AddonSpecPlanProviderImpl) CreateSpecPlan(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.AddonSpecPlanEntity,
) (*metaentity.AddonSpecPlanEntity, error) {
	specPlanModel := metamodel.AddonSpecPlanModel{}
	entity.CreatedBy = dbsCtx.BkAdditional.BkUserName
	entity.UpdatedBy = dbsCtx.BkAdditional.BkUserName

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
	entity.UpdatedBy = dbsCtx.BkAdditional.BkUserName
	if err := copier.Copy(&specPlanModel, entity); err != nil {
		return 0, errors.Wrapf(err, "failed to copy")
	}

	rows, err := a.dbAccess.Update(&specPlanModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addon spec plan with entity: %+v", entity)
	}
	return rows, nil
}

// FindSpecPlanDetails 按 addonType/addonVersion/addonTopology 查询 addon 套餐配置详情列表（含组件套餐信息）
//
// 业务约定：
//  1. addonType + addonVersion 唯一对应一个 addon
//  2. addonID + addonTopology 可对应多个 spec plan（不同 specLevel）
//
// 返回该 addon 所有规格级别的配置详情列表；任何一步未命中则返回 (nil, nil)。
func (a *AddonSpecPlanProviderImpl) FindSpecPlanDetails(
	params *metaentity.AddonSpecPlanDetailQueryParams,
) ([]*metaentity.AddonSpecPlanDetailEntity, error) {
	// 1. 根据 addonType / addonVersion 查询 addon
	addonModels, err := a.storageAddonDbAccess.FindByParams(&metaentity.AddonQueryParams{
		AddonType:    params.AddonType,
		AddonVersion: params.AddonVersion,
	})
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with params %+v", params)
	}
	if len(addonModels) == 0 {
		return nil, nil
	}
	addonModel := addonModels[0]

	// 2. 根据 addonID + addonTopology 查询所有 spec plan（不同 specLevel）
	specPlanModels, err := a.dbAccess.FindByParams(&metaentity.AddonSpecPlanQueryParams{
		AddonID:       addonModel.ID,
		AddonTopology: params.AddonTopology,
	})
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon spec plan with params %+v", params)
	}
	if len(specPlanModels) == 0 {
		return nil, nil
	}

	// 3. 遍历所有 spec plan，查询关联的组件套餐
	var details []*metaentity.AddonSpecPlanDetailEntity
	for _, specPlanModel := range specPlanModels {
		// 查询 spec plan 关联的组件套餐
		componentModels, err := a.componentSpecDbAccess.FindByParams(&metaentity.ComponentSpecPlanQueryParams{
			AddonSpecPlanID: specPlanModel.ID,
		})
		if err != nil {
			return nil, errors.Wrapf(err, "failed to find component spec plan with addonSpecPlanID %d",
				specPlanModel.ID)
		}
		components := make([]metaentity.ComponentSpecBriefEntity, 0, len(componentModels))
		for _, c := range componentModels {
			components = append(components, metaentity.ComponentSpecBriefEntity{
				ID:            c.ID,
				ComponentName: c.ComponentName,
				CPUCores:      c.CPUCores,
				MemoryGb:      c.MemoryGb,
				DiskSizeGb:    c.DiskSizeGb,
			})
		}

		// 每个 spec plan 可能有不同的 topology，使用实际的 topology 解析集群类型
		specDbmClusterType, _ := commconst.ResolveClusterType(addonModel.AddonType, specPlanModel.AddonTopology)
		details = append(details, &metaentity.AddonSpecPlanDetailEntity{
			ID:             specPlanModel.ID,
			AddonType:      addonModel.AddonType,
			AddonVersion:   addonModel.AddonVersion,
			AddonTopology:  specPlanModel.AddonTopology,
			DbmClusterType: specDbmClusterType,
			SpecLevel:      specPlanModel.SpecLevel,
			SpecLevelAlias: specPlanModel.SpecLevelAlias,
			Components:     components,
		})
	}

	return details, nil
}
