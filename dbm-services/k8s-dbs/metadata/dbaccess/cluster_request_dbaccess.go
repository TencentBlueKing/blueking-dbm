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
	"log/slog"

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
		slog.Error("Create request error", "error", err)
		return nil, err
	}
	return model, nil
}

// DeleteByID 删除元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&metamodel.ClusterRequestRecordModel{}, id)
	if result.Error != nil {
		slog.Error("Delete request error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) FindByID(id uint64) (*metamodel.ClusterRequestRecordModel, error) {
	var request metamodel.ClusterRequestRecordModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		slog.Error("Find request error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &request, nil
}

// Update 更新元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) Update(model *metamodel.ClusterRequestRecordModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update request error", "error", result.Error.Error())
		return 0, result.Error
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
	if err := k.db.Model(&metamodel.ClusterRequestRecordModel{}).Where(params).Count(&count).Error; err != nil {
		slog.Error("Count metamodel error", "error", err.Error())
		return nil, 0, err
	}
	offset := (pagination.Page - 1) * pagination.Limit
	if err := k.db.
		Offset(offset).
		Limit(pagination.Limit).
		Where(params).
		Order("created_at DESC").
		Find(&recordModels).
		Error; err != nil {
		slog.Error("List metamodel error", "error", err.Error())
		return nil, 0, err
	}

	return recordModels, uint64(count), nil
}

// NewClusterRequestRecordDbAccess 创建 ClusterRequestRecordDbAccess 接口实现实例
func NewClusterRequestRecordDbAccess(db *gorm.DB) ClusterRequestRecordDbAccess {
	return &ClusterRequestRecordDbAccessImpl{db: db}
}
