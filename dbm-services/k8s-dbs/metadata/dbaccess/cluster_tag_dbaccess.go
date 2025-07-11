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
	commconst "k8s-dbs/common/constant"
	models "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// K8sCrdClusterTagDbAccess 定义 cluster tag 元数据的数据库访问接口
type K8sCrdClusterTagDbAccess interface {
	Create(model *models.K8sCrdClusterTagModel) (*models.K8sCrdClusterTagModel, error)
	DeleteByClusterID(clusterID uint64) (uint64, error)
	FindByClusterID(clusterID uint64) ([]*models.K8sCrdClusterTagModel, error)
	BatchCreate(models []*models.K8sCrdClusterTagModel) (uint64, error)
}

// K8sCrdClusterTagDbAccessImpl AddonClusterVersionDbAccess 的具体实现
type K8sCrdClusterTagDbAccessImpl struct {
	db *gorm.DB
}

// BatchCreate 批量新增
func (k K8sCrdClusterTagDbAccessImpl) BatchCreate(models []*models.K8sCrdClusterTagModel) (uint64, error) {
	if err := k.db.Create(&models).Error; err != nil {
		return 0, err
	}
	return uint64(len(models)), nil
}

// Create 新增
func (k K8sCrdClusterTagDbAccessImpl) Create(model *models.K8sCrdClusterTagModel) (
	*models.K8sCrdClusterTagModel,
	error,
) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, err
	}
	return model, nil
}

// DeleteByClusterID 删除集群关联的 Tag
func (k K8sCrdClusterTagDbAccessImpl) DeleteByClusterID(clusterID uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterTagModel{}, "crd_cluster_id = ?", clusterID)
	if result.Error != nil {
		slog.Error("Delete cluster models error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByClusterID 查找集群关联的 Tag
func (k K8sCrdClusterTagDbAccessImpl) FindByClusterID(clusterID uint64) ([]*models.K8sCrdClusterTagModel, error) {
	var tagModels []*models.K8sCrdClusterTagModel
	if err := k.db.Limit(commconst.MaxFetchSize).
		Where("crd_cluster_id = ?", clusterID).
		Order("created_at DESC").
		Find(&tagModels).Error; err != nil {
		slog.Error("Find cluster models error", "error", err.Error())
		return nil, err
	}
	return tagModels, nil

}

// NewK8sCrdClusterTagDbAccess 创建 K8sCrdClusterTagDbAccess 接口实现实例
func NewK8sCrdClusterTagDbAccess(db *gorm.DB) K8sCrdClusterTagDbAccess {
	return &K8sCrdClusterTagDbAccessImpl{db}
}
