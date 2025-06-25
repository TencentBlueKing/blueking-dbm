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
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/dbaccess"
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

// AddonClusterHelmRepoProvider 定义 addon cluster helm repo 业务逻辑层访问接口
type AddonClusterHelmRepoProvider interface {
	CreateHelmRepo(entity *entitys.AddonClusterHelmRepoEntity) (*entitys.AddonClusterHelmRepoEntity, error)
	DeleteHelmRepoByID(id uint64) (uint64, error)
	FindHelmRepoByID(id uint64) (*entitys.AddonClusterHelmRepoEntity, error)
	FindByParams(params map[string]interface{}) (*entitys.AddonClusterHelmRepoEntity, error)
	UpdateHelmRepo(entity *entitys.AddonClusterHelmRepoEntity) (uint64, error)
	ListHelmRepos(pagination entity.Pagination) ([]entitys.AddonClusterHelmRepoEntity, error)
}

// AddonClusterHelmRepoProviderImpl AddonClusterHelmRepoProvider 具体实现
type AddonClusterHelmRepoProviderImpl struct {
	dbAccess dbaccess.AddonClusterHelmRepoDbAccess
}

// CreateHelmRepo 创建
func (a *AddonClusterHelmRepoProviderImpl) CreateHelmRepo(entity *entitys.AddonClusterHelmRepoEntity) (
	*entitys.AddonClusterHelmRepoEntity, error,
) {
	model := models.AddonClusterHelmRepoModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := a.dbAccess.Create(&model)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.AddonClusterHelmRepoEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// DeleteHelmRepoByID 通过 ID 删除
func (a *AddonClusterHelmRepoProviderImpl) DeleteHelmRepoByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindHelmRepoByID 通过 ID 查找
func (a *AddonClusterHelmRepoProviderImpl) FindHelmRepoByID(id uint64) (
	*entitys.AddonClusterHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	entity := entitys.AddonClusterHelmRepoEntity{}
	if err := copier.Copy(&entity, model); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &entity, nil
}

// FindByParams 通过 params 查找
func (a *AddonClusterHelmRepoProviderImpl) FindByParams(params map[string]interface{}) (
	*entitys.AddonClusterHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByParams(params)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	entity := entitys.AddonClusterHelmRepoEntity{}
	if err := copier.Copy(&entity, model); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &entity, nil
}

// UpdateHelmRepo 更新
func (a *AddonClusterHelmRepoProviderImpl) UpdateHelmRepo(entity *entitys.AddonClusterHelmRepoEntity) (
	uint64,
	error,
) {
	model := models.AddonClusterHelmRepoModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := a.dbAccess.Update(&model)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// ListHelmRepos 分页查询
func (a *AddonClusterHelmRepoProviderImpl) ListHelmRepos(pagination entity.Pagination) (
	[]entitys.AddonClusterHelmRepoEntity,
	error,
) {
	repoModels, _, err := a.dbAccess.ListByPage(pagination)
	if err != nil {
		slog.Error("Failed to list models", "error", err)
		return nil, err
	}
	var repoEntities []entitys.AddonClusterHelmRepoEntity
	if err := copier.Copy(&repoEntities, repoModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return repoEntities, nil
}

// NewAddonClusterHelmRepoProvider 创建 AddonClusterHelmRepoDbAccess 接口实现实例
func NewAddonClusterHelmRepoProvider(dbAccess dbaccess.AddonClusterHelmRepoDbAccess) AddonClusterHelmRepoProvider {
	return &AddonClusterHelmRepoProviderImpl{dbAccess: dbAccess}
}
