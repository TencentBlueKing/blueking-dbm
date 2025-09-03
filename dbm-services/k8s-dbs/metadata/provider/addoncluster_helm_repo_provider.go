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

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// AddonClusterHelmRepoProvider 定义 addon cluster helm repo 业务逻辑层访问接口
type AddonClusterHelmRepoProvider interface {
	CreateHelmRepo(
		dbsCtx *commentity.DbsContext,
		entity *metaentity.AddonClusterHelmRepoEntity,
	) (*metaentity.AddonClusterHelmRepoEntity, error)
	DeleteHelmRepoByID(id uint64) (uint64, error)
	FindHelmRepoByID(id uint64) (*metaentity.AddonClusterHelmRepoEntity, error)
	FindByParams(params *metaentity.HelmRepoQueryParams) (*metaentity.AddonClusterHelmRepoEntity, error)
	UpdateHelmRepo(entity *metaentity.AddonClusterHelmRepoEntity) (uint64, error)
	ListHelmRepos(pagination commentity.Pagination) ([]*metaentity.AddonClusterHelmRepoEntity, error)
}

// AddonClusterHelmRepoProviderImpl AddonClusterHelmRepoProvider 具体实现
type AddonClusterHelmRepoProviderImpl struct {
	dbAccess dbaccess.AddonClusterHelmRepoDbAccess
}

// CreateHelmRepo 创建
func (a *AddonClusterHelmRepoProviderImpl) CreateHelmRepo(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.AddonClusterHelmRepoEntity,
) (*metaentity.AddonClusterHelmRepoEntity, error) {
	model := metamodel.AddonClusterHelmRepoModel{}
	entity.CreatedBy = dbsCtx.BkAuth.BkUserName
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName
	if err := copier.Copy(&model, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addedModel, err := a.dbAccess.Create(&model)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addoncluster helm repo with entity: %+v", entity)
	}

	addedEntity := metaentity.AddonClusterHelmRepoEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	return &addedEntity, nil
}

// DeleteHelmRepoByID 通过 ID 删除
func (a *AddonClusterHelmRepoProviderImpl) DeleteHelmRepoByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindHelmRepoByID 通过 ID 查找
func (a *AddonClusterHelmRepoProviderImpl) FindHelmRepoByID(id uint64) (
	*metaentity.AddonClusterHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addoncluster helm repo with id %d", id)
	}
	repoEntity := metaentity.AddonClusterHelmRepoEntity{}
	if err = copier.Copy(&repoEntity, model); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &repoEntity, nil
}

// FindByParams 通过 params 查找
func (a *AddonClusterHelmRepoProviderImpl) FindByParams(params *metaentity.HelmRepoQueryParams) (
	*metaentity.AddonClusterHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addoncluster helm repo with params %+v", params)
	}
	repoEntity := metaentity.AddonClusterHelmRepoEntity{}
	if err = copier.Copy(&repoEntity, model); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &repoEntity, nil
}

// UpdateHelmRepo 更新
func (a *AddonClusterHelmRepoProviderImpl) UpdateHelmRepo(entity *metaentity.AddonClusterHelmRepoEntity) (
	uint64,
	error,
) {
	model := metamodel.AddonClusterHelmRepoModel{}
	if err := copier.Copy(&model, entity); err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}

	rows, err := a.dbAccess.Update(&model)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addoncluster helm repo with entity: %+v", entity)
	}
	return rows, nil
}

// ListHelmRepos 分页查询
func (a *AddonClusterHelmRepoProviderImpl) ListHelmRepos(pagination commentity.Pagination) (
	[]*metaentity.AddonClusterHelmRepoEntity,
	error,
) {
	repoModels, _, err := a.dbAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list addoncluster helm repo with pagination: %+v", pagination)
	}
	var repoEntities []*metaentity.AddonClusterHelmRepoEntity
	if err := copier.Copy(&repoEntities, repoModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return repoEntities, nil
}

// NewAddonClusterHelmRepoProvider 创建 AddonClusterHelmRepoDbAccess 接口实现实例
func NewAddonClusterHelmRepoProvider(dbAccess dbaccess.AddonClusterHelmRepoDbAccess) AddonClusterHelmRepoProvider {
	return &AddonClusterHelmRepoProviderImpl{dbAccess: dbAccess}
}
