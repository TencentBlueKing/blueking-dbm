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
	"k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"gorm.io/gorm"
)

// K8sCrdClusterDbAccess 定义 cluster 元数据的数据库访问接口
type K8sCrdClusterDbAccess interface {
	Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdClusterModel, error)
	FindByParams(params *metaentity.ClusterQueryParams) (*models.K8sCrdClusterModel, error)
	Update(model *models.K8sCrdClusterModel) (uint64, error)
	ListByPage(params *metaentity.ClusterQueryParams, pagination *entity.Pagination) (
		[]*models.K8sCrdClusterModel, uint64, error)
}

// K8sCrdClusterDbAccessImpl K8sCrdClusterDbAccess 的具体实现
type K8sCrdClusterDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create cluster with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete cluster with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 根据 ID 查找 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) FindByID(id uint64) (*models.K8sCrdClusterModel, error) {
	var cluster models.K8sCrdClusterModel
	result := k.db.First(&cluster, id)
	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find cluster with id %d", id)
	}
	return &cluster, nil
}

// FindByParams 根据参数查找 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) FindByParams(params *metaentity.ClusterQueryParams) (
	*models.K8sCrdClusterModel,
	error,
) {
	var cluster models.K8sCrdClusterModel
	query := k.db.Where(&models.K8sCrdClusterModel{})
	if params.K8sClusterConfigID > 0 {
		query = query.Where("k8s_cluster_config_id = ?", params.K8sClusterConfigID)
	}
	if params.Namespace != "" {
		query = query.Where("namespace = ?", params.Namespace)
	}
	if params.ClusterName != "" {
		query = query.Where("cluster_name = ?", params.ClusterName)
	}
	result := query.First(&cluster)
	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find cluster with params %+v", params)
	}
	return &cluster, nil
}

// Update 更新 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) Update(model *models.K8sCrdClusterModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update cluster with model %+v", model)
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) ListByPage(
	params *metaentity.ClusterQueryParams,
	pagination *entity.Pagination,
) ([]*models.K8sCrdClusterModel, uint64, error) {
	var clusterModels []*models.K8sCrdClusterModel
	var count int64
	query := k.db.Debug().Model(&models.K8sCrdClusterModel{})
	if len(params.Creators) > 0 {
		query = query.Where("created_by in (?)", params.Creators)
	}
	if len(params.Updaters) > 0 {
		query = query.Where("updated_by in (?)", params.Updaters)
	}
	if params.ClusterName != "" {
		query = query.Where("cluster_name like ?", "%"+params.ClusterName+"%")
	}
	if params.ClusterAlias != "" {
		query = query.Where("cluster_alias like ?", "%"+params.ClusterAlias+"%")
	}
	if params.BkBizName != "" {
		query = query.Where("bk_biz_name like ?", "%"+params.BkBizName+"%")
	}
	if len(params.BkBizIDs) > 0 {
		query = query.Where("bk_biz_id in (?)", params.BkBizIDs)
	}
	if params.Namespace != "" {
		query = query.Where("namespace = ?", params.Namespace)
	}
	if len(params.AddonTypes) > 0 {
		subQuery := k.db.Debug().Model(&models.K8sCrdStorageAddonModel{}).
			Select("id").
			Where("addon_type in (?)", params.AddonTypes)
		query = query.Where("addon_id in (?)", subQuery)
	}

	if err := query.Count(&count).Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to count cluster with pagination %+v", pagination)
	}
	offset := (pagination.Page - 1) * pagination.Limit
	if err := query.
		Offset(offset).
		Limit(pagination.Limit).
		Order("created_at DESC").
		Find(&clusterModels).
		Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to list cluster with pagination %+v", pagination)
	}

	return clusterModels, uint64(count), nil
}

// NewCrdClusterDbAccess 创建 K8sCrdClusterDbAccess 接口实现实例
func NewCrdClusterDbAccess(db *gorm.DB) K8sCrdClusterDbAccess {
	return &K8sCrdClusterDbAccessImpl{db: db}
}
