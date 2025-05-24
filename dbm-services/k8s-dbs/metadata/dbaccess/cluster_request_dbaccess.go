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
	"fmt"
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

// ClusterRequestRecordDbAccess 定义 request record 元数据的数据库访问接口
type ClusterRequestRecordDbAccess interface {
	Create(model *models.ClusterRequestRecordModel) (*models.ClusterRequestRecordModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.ClusterRequestRecordModel, error)
	Update(model *models.ClusterRequestRecordModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.ClusterRequestRecordModel, int64, error)
}

// ClusterRequestRecordDbAccessImpl ClusterRequestRecordDbAccess 的具体实现
type ClusterRequestRecordDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) Create(model *models.ClusterRequestRecordModel) (
	*models.ClusterRequestRecordModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create request error", "error", err)
		return nil, err
	}
	var addedRequest models.ClusterRequestRecordModel
	if err := k.db.First(&addedRequest, "id=?", model.ID).Error; err != nil {
		slog.Error("Find request error", "error", err)
		return nil, err
	}
	return &addedRequest, nil
}

// DeleteByID 删除元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.ClusterRequestRecordModel{}, id)
	if result.Error != nil {
		slog.Error("Delete request error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) FindByID(id uint64) (*models.ClusterRequestRecordModel, error) {
	var request models.ClusterRequestRecordModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		slog.Error("Find request error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &request, nil
}

// Update 更新元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) Update(model *models.ClusterRequestRecordModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update request error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *ClusterRequestRecordDbAccessImpl) ListByPage(_ utils.Pagination) (
	[]models.ClusterRequestRecordModel,
	int64,
	error,
) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewClusterRequestRecordDbAccess 创建 ClusterRequestRecordDbAccess 接口实现实例
func NewClusterRequestRecordDbAccess(db *gorm.DB) ClusterRequestRecordDbAccess {
	return &ClusterRequestRecordDbAccessImpl{db: db}
}
