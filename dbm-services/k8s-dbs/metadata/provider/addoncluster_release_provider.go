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
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// AddonClusterReleaseProvider 定义 addon cluster release 业务逻辑层访问接口
type AddonClusterReleaseProvider interface {
	CreateClusterRelease(entity *metaentity.AddonClusterReleaseEntity) (*metaentity.AddonClusterReleaseEntity, error)
	DeleteClusterReleaseByID(id uint64) (uint64, error)
	FindClusterReleaseByID(id uint64) (*metaentity.AddonClusterReleaseEntity, error)
	FindByParams(params *metaentity.ClusterReleaseQueryParams) (*metaentity.AddonClusterReleaseEntity, error)
	UpdateClusterRelease(entity *metaentity.AddonClusterReleaseEntity) (uint64, error)
	ListClusterReleases(pagination entity.Pagination) ([]*metaentity.AddonClusterReleaseEntity, error)
}

// AddonClusterReleaseProviderImpl AddonClusterReleaseProvider 具体实现
type AddonClusterReleaseProviderImpl struct {
	dbAccess dbaccess.AddonClusterReleaseDbAccess
}

// CreateClusterRelease 创建 cluster release
func (a *AddonClusterReleaseProviderImpl) CreateClusterRelease(entity *metaentity.AddonClusterReleaseEntity) (
	*metaentity.AddonClusterReleaseEntity, error,
) {
	releaseModel := metamodel.AddonClusterReleaseModel{}
	if err := copier.Copy(&releaseModel, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addedModel, err := a.dbAccess.Create(&releaseModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addoncluster release with entity: %+v", entity)
	}

	addedEntity := metaentity.AddonClusterReleaseEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	return &addedEntity, nil
}

// DeleteClusterReleaseByID 删除 cluster release
func (a *AddonClusterReleaseProviderImpl) DeleteClusterReleaseByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindClusterReleaseByID 查找 cluster release
func (a *AddonClusterReleaseProviderImpl) FindClusterReleaseByID(id uint64) (
	*metaentity.AddonClusterReleaseEntity,
	error,
) {
	releaseModel, err := a.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addoncluster release with id %d", id)
	}

	releaseEntity := metaentity.AddonClusterReleaseEntity{}
	if err = copier.Copy(&releaseEntity, releaseModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return &releaseEntity, nil
}

// FindByParams 通过 params 查找 addon cluster release
func (a *AddonClusterReleaseProviderImpl) FindByParams(params *metaentity.ClusterReleaseQueryParams) (
	*metaentity.AddonClusterReleaseEntity,
	error,
) {
	clusterReleaseModel, err := a.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addoncluster release with params %+v", params)
	}
	clusterReleaseEntity := metaentity.AddonClusterReleaseEntity{}
	if err := copier.Copy(&clusterReleaseEntity, clusterReleaseModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return &clusterReleaseEntity, nil
}

// UpdateClusterRelease 更新 cluster release
func (a *AddonClusterReleaseProviderImpl) UpdateClusterRelease(entity *metaentity.AddonClusterReleaseEntity) (
	uint64,
	error,
) {
	releaseModel := metamodel.AddonClusterReleaseModel{}
	if err := copier.Copy(&releaseModel, entity); err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}

	rows, err := a.dbAccess.Update(&releaseModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addoncluster release with entity: %+v", entity)
	}
	return rows, nil
}

// ListClusterReleases 获取 addon cluster release 列表
func (a *AddonClusterReleaseProviderImpl) ListClusterReleases(pagination entity.Pagination) (
	[]*metaentity.AddonClusterReleaseEntity,
	error,
) {
	releaseModels, _, err := a.dbAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list addoncluster releases with pagination: %+v", pagination)
	}
	var releaseEntities []*metaentity.AddonClusterReleaseEntity
	if err = copier.Copy(&releaseEntities, releaseModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return releaseEntities, nil
}

// NewAddonClusterReleaseProvider 创建 AddonClusterReleaseDbAccess 接口实现实例
func NewAddonClusterReleaseProvider(dbAccess dbaccess.AddonClusterReleaseDbAccess) AddonClusterReleaseProvider {
	return &AddonClusterReleaseProviderImpl{dbAccess: dbAccess}
}
