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

// K8sCrdStorageAddonProvider 定义 addon 业务逻辑层访问接口
type K8sCrdStorageAddonProvider interface {
	CreateStorageAddon(dbsCtx *commentity.DbsContext, entity *metaentity.K8sCrdStorageAddonEntity) (
		*metaentity.K8sCrdStorageAddonEntity, error)
	DeleteStorageAddonByID(id uint64) (uint64, error)
	FindStorageAddonByID(id uint64) (*metaentity.K8sCrdStorageAddonEntity, error)
	FindVersionsByParams(params *metaentity.AddonVersionQueryParams) ([]*metaentity.AddonVersionEntity, error)
	FindStorageAddonByParams(params *metaentity.AddonQueryParams) ([]*metaentity.K8sCrdStorageAddonEntity, error)
	UpdateStorageAddon(dbsCtx *commentity.DbsContext, entity *metaentity.K8sCrdStorageAddonEntity) (uint64, error)
	ListStorageAddons(pagination commentity.Pagination) ([]*metaentity.K8sCrdStorageAddonEntity, error)
}

// K8sCrdStorageAddonProviderImpl K8sCrdStorageAddonProvider 具体实现
type K8sCrdStorageAddonProviderImpl struct {
	dbAccess dbaccess.K8sCrdStorageAddonDbAccess
}

// FindVersionsByParams 按照参数查询 addon 版本信息
func (k *K8sCrdStorageAddonProviderImpl) FindVersionsByParams(params *metaentity.AddonVersionQueryParams) (
	[]*metaentity.AddonVersionEntity,
	error,
) {
	versionModels, err := k.dbAccess.FindVersionsByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon versions with params %+v", params)
	}
	var versionEntities []*metaentity.AddonVersionEntity
	if err = copier.Copy(&versionEntities, versionModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return versionEntities, nil
}

// FindStorageAddonByParams 按照参数进行查询
func (k *K8sCrdStorageAddonProviderImpl) FindStorageAddonByParams(params *metaentity.AddonQueryParams) (
	[]*metaentity.K8sCrdStorageAddonEntity,
	error,
) {
	addonModels, err := k.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with params %+v", params)
	}
	var addonEntities []*metaentity.K8sCrdStorageAddonEntity
	if err = copier.Copy(&addonEntities, addonModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return addonEntities, nil
}

// CreateStorageAddon 创建 addon
func (k *K8sCrdStorageAddonProviderImpl) CreateStorageAddon(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.K8sCrdStorageAddonEntity,
) (*metaentity.K8sCrdStorageAddonEntity, error) {
	storageAddonModel := metamodel.K8sCrdStorageAddonModel{}
	entity.CreatedBy = dbsCtx.BkAuth.BkUserName
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName

	if err := copier.Copy(&storageAddonModel, entity); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	addedStorageAddonModel, err := k.dbAccess.Create(&storageAddonModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create addon with entity: %+v", entity)
	}

	storageAddonEntity := metaentity.K8sCrdStorageAddonEntity{}
	if err = copier.Copy(&storageAddonEntity, addedStorageAddonModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}

	return &storageAddonEntity, nil
}

// DeleteStorageAddonByID 删除 addon
func (k *K8sCrdStorageAddonProviderImpl) DeleteStorageAddonByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindStorageAddonByID 按照 ID 进行查询
func (k *K8sCrdStorageAddonProviderImpl) FindStorageAddonByID(id uint64) (*metaentity.K8sCrdStorageAddonEntity, error) {
	storageAddonModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with id %d", id)
	}
	storageAddonEntity := metaentity.K8sCrdStorageAddonEntity{}
	if err = copier.Copy(&storageAddonEntity, storageAddonModel); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return &storageAddonEntity, nil
}

// UpdateStorageAddon 更新 addon
func (k *K8sCrdStorageAddonProviderImpl) UpdateStorageAddon(
	dbsCtx *commentity.DbsContext,
	entity *metaentity.K8sCrdStorageAddonEntity,
) (uint64, error) {
	storageAddonModel := metamodel.K8sCrdStorageAddonModel{}
	entity.UpdatedBy = dbsCtx.BkAuth.BkUserName
	if err := copier.Copy(&storageAddonModel, entity); err != nil {
		return 0, errors.Wrapf(err, "failed to copy")
	}

	rows, err := k.dbAccess.Update(&storageAddonModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update addon with entity: %+v", entity)
	}
	return rows, nil
}

// ListStorageAddons 获取 addon 列表
func (k *K8sCrdStorageAddonProviderImpl) ListStorageAddons(pagination commentity.Pagination) (
	[]*metaentity.K8sCrdStorageAddonEntity,
	error,
) {
	addonModels, _, err := k.dbAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list addons with pagination: %+v", pagination)
	}
	var storageAddons []*metaentity.K8sCrdStorageAddonEntity
	if err = copier.Copy(&storageAddons, addonModels); err != nil {
		return nil, errors.Wrapf(err, "failed to copy")
	}
	return storageAddons, nil
}

// NewK8sCrdStorageAddonProvider 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewK8sCrdStorageAddonProvider(dbAccess dbaccess.K8sCrdStorageAddonDbAccess) K8sCrdStorageAddonProvider {
	return &K8sCrdStorageAddonProviderImpl{dbAccess: dbAccess}
}
