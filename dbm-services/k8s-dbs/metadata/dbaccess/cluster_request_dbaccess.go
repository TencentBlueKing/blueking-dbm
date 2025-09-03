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
	metamodel "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"gorm.io/gorm"
)

// ClusterRequestRecordDbAccess 定义 request record 元数据的数据库访问接口
type ClusterRequestRecordDbAccess interface {
	Create(model *metamodel.ClusterRequestRecordModel) (*metamodel.ClusterRequestRecordModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*metamodel.ClusterRequestRecordModel, error)
	Update(model *metamodel.ClusterRequestRecordModel) (uint64, error)
	ListByPage(params *metaentity.ClusterRequestQueryParams, pagination *entity.Pagination) (
		[]*metamodel.ClusterRequestRecordModel, uint64, error)
}

// ClusterRequestRecordDbAccessImpl ClusterRequestRecordDbAccess 的具体实现
type ClusterRequestRecordDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) Create(model *metamodel.ClusterRequestRecordModel) (
	*metamodel.ClusterRequestRecordModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create request record with model %+v", model)
	}
	return model, nil
}

// DeleteByID 删除元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&metamodel.ClusterRequestRecordModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete request record with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) FindByID(id uint64) (*metamodel.ClusterRequestRecordModel, error) {
	var request metamodel.ClusterRequestRecordModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find request record with id %d", id)
	}
	return &request, nil
}

// Update 更新元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) Update(model *metamodel.ClusterRequestRecordModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update request record with model %+v", model)
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) ListByPage(
	params *metaentity.ClusterRequestQueryParams,
	pagination *entity.Pagination,
) (
	[]*metamodel.ClusterRequestRecordModel,
	uint64,
	error,
) {
	var recordModels []*metamodel.ClusterRequestRecordModel
	var count int64
	query := k.db.Debug().Model(&metamodel.ClusterRequestRecordModel{})
	if params.K8sClusterName != "" {
		query = query.Where("k8s_cluster_name = ?", params.K8sClusterName)
	}
	if params.NameSpace != "" {
		query = query.Where("namespace = ?", params.NameSpace)
	}
	if len(params.Creators) > 0 {
		query = query.Where("created_by in ?", params.Creators)
	}
	if !params.StartTime.IsZero() {
		query = query.Where("created_at >= ?", params.StartTime)

	}
	if !params.EndTime.IsZero() {
		query = query.Where("created_at <= ?", params.EndTime)
	}

	if len(params.RequestTypes) > 0 {
		query = query.Where("request_type in ?", params.RequestTypes)
	}

	if len(params.ClusterNames) > 0 {
		query = query.Where("cluster_name in ?", params.ClusterNames)
	}

	if params.RequestParams != "" {
		query = query.Where("request_params like ?", "%"+params.RequestParams+"%")
	}

	if err := query.Count(&count).Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to count request record with pagination %+v", pagination)
	}

	offset := (pagination.Page - 1) * pagination.Limit
	if err := query.
		Offset(offset).
		Limit(pagination.Limit).
		Order("created_at DESC").
		Find(&recordModels).
		Error; err != nil {
		return nil, 0, errors.Wrapf(err, "failed to find request record with pagination %+v", pagination)
	}
	return recordModels, uint64(count), nil
}

// NewClusterRequestRecordDbAccess 创建 ClusterRequestRecordDbAccess 接口实现实例
func NewClusterRequestRecordDbAccess(db *gorm.DB) ClusterRequestRecordDbAccess {
	return &ClusterRequestRecordDbAccessImpl{db: db}
}
