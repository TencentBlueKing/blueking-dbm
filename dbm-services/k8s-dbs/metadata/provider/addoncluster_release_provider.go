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

// AddonClusterReleaseProvider 定义 addon cluster release 业务逻辑层访问接口
type AddonClusterReleaseProvider interface {
	CreateClusterRelease(entity *entitys.AddonClusterReleaseEntity) (*entitys.AddonClusterReleaseEntity, error)
	DeleteClusterReleaseByID(id uint64) (uint64, error)
	FindClusterReleaseByID(id uint64) (*entitys.AddonClusterReleaseEntity, error)
	FindByParams(params map[string]interface{}) (*entitys.AddonClusterReleaseEntity, error)
	UpdateClusterRelease(entity *entitys.AddonClusterReleaseEntity) (uint64, error)
	ListClusterReleases(pagination entity.Pagination) ([]*entitys.AddonClusterReleaseEntity, error)
}

// AddonClusterReleaseProviderImpl AddonClusterReleaseProvider 具体实现
type AddonClusterReleaseProviderImpl struct {
	dbAccess dbaccess.AddonClusterReleaseDbAccess
}

// CreateClusterRelease 创建 cluster release
func (a *AddonClusterReleaseProviderImpl) CreateClusterRelease(entity *entitys.AddonClusterReleaseEntity) (
	*entitys.AddonClusterReleaseEntity, error,
) {
	releaseModel := models.AddonClusterReleaseModel{}
	err := copier.Copy(&releaseModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := a.dbAccess.Create(&releaseModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.AddonClusterReleaseEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// DeleteClusterReleaseByID 删除 cluster release
func (a *AddonClusterReleaseProviderImpl) DeleteClusterReleaseByID(id uint64) (uint64, error) {
	return a.dbAccess.DeleteByID(id)
}

// FindClusterReleaseByID 查找 cluster release
func (a *AddonClusterReleaseProviderImpl) FindClusterReleaseByID(id uint64) (
	*entitys.AddonClusterReleaseEntity,
	error,
) {
	releaseModel, err := a.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	releaseEntity := entitys.AddonClusterReleaseEntity{}
	if err := copier.Copy(&releaseEntity, releaseModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &releaseEntity, nil
}

// FindByParams 通过 params 查找 addon cluster release
func (a *AddonClusterReleaseProviderImpl) FindByParams(params map[string]interface{}) (
	*entitys.AddonClusterReleaseEntity,
	error,
) {
	clusterReleaseModel, err := a.dbAccess.FindByParams(params)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	clusterReleaseEntity := entitys.AddonClusterReleaseEntity{}
	if err := copier.Copy(&clusterReleaseEntity, clusterReleaseModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &clusterReleaseEntity, nil
}

// UpdateClusterRelease 更新 cluster release
func (a *AddonClusterReleaseProviderImpl) UpdateClusterRelease(entity *entitys.AddonClusterReleaseEntity) (
	uint64,
	error,
) {
	releaseModel := models.AddonClusterReleaseModel{}
	err := copier.Copy(&releaseModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := a.dbAccess.Update(&releaseModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// ListClusterReleases 获取 addon cluster release 列表
func (a *AddonClusterReleaseProviderImpl) ListClusterReleases(pagination entity.Pagination) (
	[]*entitys.AddonClusterReleaseEntity,
	error,
) {
	releaseModels, _, err := a.dbAccess.ListByPage(pagination)
	if err != nil {
		slog.Error("Failed to find release")
		return nil, err
	}
	var releaseEntities []*entitys.AddonClusterReleaseEntity
	if err := copier.Copy(&releaseEntities, releaseModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return releaseEntities, nil
}

// NewAddonClusterReleaseProvider 创建 AddonClusterReleaseDbAccess 接口实现实例
func NewAddonClusterReleaseProvider(dbAccess dbaccess.AddonClusterReleaseDbAccess) AddonClusterReleaseProvider {
	return &AddonClusterReleaseProviderImpl{dbAccess: dbAccess}
}
