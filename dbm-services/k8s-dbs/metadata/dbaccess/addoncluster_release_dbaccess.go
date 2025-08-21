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
	"errors"
	"fmt"
	commentity "k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// AddonClusterReleaseDbAccess 定义 AddonClusterRelease 元数据的数据库访问接口
type AddonClusterReleaseDbAccess interface {
	Create(model *metamodel.AddonClusterReleaseModel) (*metamodel.AddonClusterReleaseModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.AddonClusterReleaseModel, error)
	FindByParams(params *metaentity.ClusterReleaseQueryParams) (*metamodel.AddonClusterReleaseModel, error)
	Update(model *metamodel.AddonClusterReleaseModel) (uint64, error)
	ListByPage(pagination commentity.Pagination) ([]metamodel.AddonClusterReleaseModel, int64, error)
}

// AddonClusterReleaseDbAccessImpl AddonClusterReleaseDbAccess 的具体实现
type AddonClusterReleaseDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) Create(model *metamodel.AddonClusterReleaseModel) (
	*metamodel.AddonClusterReleaseModel, error,
) {
	if err := a.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	return model, nil
}

// DeleteByID 删除 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := a.db.Delete(&metamodel.AddonClusterReleaseModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) FindByID(id uint64) (*metamodel.AddonClusterReleaseModel, error) {
	var model metamodel.AddonClusterReleaseModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &model, nil
}

// FindByParams 根据参数查找 addon cluster release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) FindByParams(params *metaentity.ClusterReleaseQueryParams) (
	*metamodel.AddonClusterReleaseModel,
	error,
) {
	var clusterRelease metamodel.AddonClusterReleaseModel
	result := a.db.Where(params).First(&clusterRelease)
	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, fmt.Errorf("cluster release not found")
	}
	if result.Error != nil {
		return nil, result.Error
	}
	return &clusterRelease, nil
}

// Update 更新 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) Update(model *metamodel.AddonClusterReleaseModel) (uint64, error) {
	result := a.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) ListByPage(pagination commentity.Pagination) (
	[]metamodel.AddonClusterReleaseModel,
	int64,
	error,
) {
	var releaseModels []metamodel.AddonClusterReleaseModel
	if err := a.db.Offset(pagination.Page).Limit(pagination.Limit).Find(&releaseModels).Error; err != nil {
		slog.Error("List release error", "error", err.Error())
		return nil, 0, err
	}
	return releaseModels, int64(len(releaseModels)), nil
}

// NewAddonClusterReleaseDbAccess 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewAddonClusterReleaseDbAccess(db *gorm.DB) AddonClusterReleaseDbAccess {
	return &AddonClusterReleaseDbAccessImpl{db: db}
}
