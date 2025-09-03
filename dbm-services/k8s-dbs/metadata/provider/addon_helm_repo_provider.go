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

// AddonHelmRepoProvider 定义 addon cluster helm repo 业务逻辑层访问接口
type AddonHelmRepoProvider interface {
	CreateHelmRepo(
		dbsCtx *commentity.DbsContext,
		entity *metaentity.AddonHelmRepoEntity,
	) (*metaentity.AddonHelmRepoEntity, error)
	DeleteHelmRepoByID(id uint64) (uint64, error)
	FindHelmRepoByID(id uint64) (*metaentity.AddonHelmRepoEntity, error)
	FindByParams(params *metaentity.HelmRepoQueryParams) (*metaentity.AddonHelmRepoEntity, error)
	UpdateHelmRepo(entity *metaentity.AddonHelmRepoEntity) (uint64, error)
	ListHelmRepos(pagination commentity.Pagination) ([]*metaentity.AddonHelmRepoEntity, error)
}

// AddonHelmRepoProviderImpl AddonHelmRepoProvider 具体实现
type AddonHelmRepoProviderImpl struct {
	dbAccess dbaccess.AddonHelmRepoDbAccess
}

// CreateHelmRepo 创建
func (a *AddonHelmRepoProviderImpl) CreateHelmRepo(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.AddonHelmRepoEntity,
) (*metaentity.AddonHelmRepoEntity, error) {
	model := metamodel.AddonHelmRepoModel{}
	entity.CreatedBy = dbsCtx.BkAuth.BkUserName
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName
	if err := copier.Copy(&model, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	addedModel, err := a.dbAccess.Create(&model)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addon helm repo with entity %+v", entity)
	}
	addedEntity := metaentity.AddonHelmRepoEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &addedEntity, nil
}

// DeleteHelmRepoByID 通过 ID 删除
func (a *AddonHelmRepoProviderImpl) DeleteHelmRepoByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindHelmRepoByID 通过 ID 查找
func (a *AddonHelmRepoProviderImpl) FindHelmRepoByID(id uint64) (
	*metaentity.AddonHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon helm repo with id %d", id)
	}
	repoEntity := metaentity.AddonHelmRepoEntity{}
	if err := copier.Copy(&repoEntity, model); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &repoEntity, nil
}

// FindByParams 通过 params 查找
func (a *AddonHelmRepoProviderImpl) FindByParams(params *metaentity.HelmRepoQueryParams) (
	*metaentity.AddonHelmRepoEntity,
	error,
) {
	model, err := a.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon helm repo with params %+v", params)
	}
	repoEntity := metaentity.AddonHelmRepoEntity{}
	if err := copier.Copy(&repoEntity, model); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &repoEntity, nil
}

// UpdateHelmRepo 更新
func (a *AddonHelmRepoProviderImpl) UpdateHelmRepo(entity *metaentity.AddonHelmRepoEntity) (
	uint64,
	error,
) {
	model := metamodel.AddonHelmRepoModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}
	rows, err := a.dbAccess.Update(&model)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addon helm repo with entity %+v", entity)
	}
	return rows, nil
}

// ListHelmRepos 分页查询
func (a *AddonHelmRepoProviderImpl) ListHelmRepos(pagination commentity.Pagination) (
	[]*metaentity.AddonHelmRepoEntity,
	error,
) {
	repoModels, _, err := a.dbAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list addon helm repos pagination %+v", pagination)
	}
	var repoEntities []*metaentity.AddonHelmRepoEntity
	if err := copier.Copy(&repoEntities, repoModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return repoEntities, nil
}

// NewAddonHelmRepoProvider 创建 AddonHelmRepoDbAccess 接口实现实例
func NewAddonHelmRepoProvider(dbAccess dbaccess.AddonHelmRepoDbAccess) AddonHelmRepoProvider {
	return &AddonHelmRepoProviderImpl{dbAccess: dbAccess}
}
