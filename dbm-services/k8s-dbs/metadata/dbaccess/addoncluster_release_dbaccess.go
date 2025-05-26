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
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log"
	"log/slog"

	"gorm.io/gorm"
)

// AddonClusterReleaseDbAccess 定义 AddonClusterRelease 元数据的数据库访问接口
type AddonClusterReleaseDbAccess interface {
	Create(model *models.AddonClusterReleaseModel) (*models.AddonClusterReleaseModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.AddonClusterReleaseModel, error)
	FindByParams(params map[string]interface{}) (*models.AddonClusterReleaseModel, error)
	Update(model *models.AddonClusterReleaseModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.AddonClusterReleaseModel, int64, error)
}

// AddonClusterReleaseDbAccessImpl AddonClusterReleaseDbAccess 的具体实现
type AddonClusterReleaseDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) Create(model *models.AddonClusterReleaseModel) (
	*models.AddonClusterReleaseModel, error,
) {
	if err := a.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	var addedModel models.AddonClusterReleaseModel
	if err := a.db.First(&addedModel, "release_name = ? and namespace = ? and k8s_cluster_config_id = ?",
		model.ReleaseName, model.Namespace, model.K8sClusterConfigID).Error; err != nil {
		slog.Error("Find model error", "error", err)
		return nil, err
	}
	return &addedModel, nil
}

// DeleteByID 删除 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := a.db.Delete(&models.AddonClusterReleaseModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) FindByID(id uint64) (*models.AddonClusterReleaseModel, error) {
	var model models.AddonClusterReleaseModel
	result := a.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &model, nil
}

// FindByParams 根据参数查找 addon cluster release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) FindByParams(params map[string]interface{}) (
	*models.AddonClusterReleaseModel,
	error,
) {
	var clusterRelease models.AddonClusterReleaseModel

	// 动态条件查询
	result := a.db.Where(params).First(&clusterRelease)

	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, fmt.Errorf("cluster release not found")
	}
	if result.Error != nil {
		log.Printf("Query cluster release error: %v", result.Error)
		return nil, result.Error
	}

	return &clusterRelease, nil
}

// Update 更新 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) Update(model *models.AddonClusterReleaseModel) (uint64, error) {
	result := a.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 AddonCluster Release 元数据接口实现
func (a *AddonClusterReleaseDbAccessImpl) ListByPage(pagination utils.Pagination) (
	[]models.AddonClusterReleaseModel,
	int64,
	error,
) {
	var releaseModels []models.AddonClusterReleaseModel
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
