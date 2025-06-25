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
	"k8s-dbs/common/entity"
	models "k8s-dbs/metadata/dbaccess/model"
	"log"
	"log/slog"

	"gorm.io/gorm"
)

// K8sCrdClusterDbAccess 定义 cluster 元数据的数据库访问接口
type K8sCrdClusterDbAccess interface {
	Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdClusterModel, error)
	FindByParams(params map[string]interface{}) (*models.K8sCrdClusterModel, error)
	Update(model *models.K8sCrdClusterModel) (uint64, error)
	ListByPage(params map[string]interface{}, pagination *entity.Pagination) ([]models.K8sCrdClusterModel, uint64, error)
}

// K8sCrdClusterDbAccessImpl K8sCrdClusterDbAccess 的具体实现
type K8sCrdClusterDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create cluster error", "error", err)
		return nil, err
	}
	return model, nil
}

// DeleteByID 删除 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterModel{}, id)
	if result.Error != nil {
		slog.Error("Delete cluster error:", "error", result.Error)
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 根据 ID 查找 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) FindByID(id uint64) (*models.K8sCrdClusterModel, error) {
	var cluster models.K8sCrdClusterModel
	result := k.db.First(&cluster, id)
	if result.Error != nil {
		slog.Error("Find cluster error", "error", result.Error)
		return nil, result.Error
	}
	return &cluster, nil
}

// FindByParams 根据参数查找 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) FindByParams(params map[string]interface{}) (*models.K8sCrdClusterModel, error) {
	var cluster models.K8sCrdClusterModel

	// 动态条件查询
	result := k.db.Where(params).First(&cluster)

	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, fmt.Errorf("cluster not found")
	}
	if result.Error != nil {
		log.Printf("Query cluster error: %v", result.Error)
		return nil, result.Error
	}

	return &cluster, nil
}

// Update 更新 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) Update(model *models.K8sCrdClusterModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update cluster error:", "error", result.Error)
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 cluster 元数据接口实现
func (k *K8sCrdClusterDbAccessImpl) ListByPage(
	params map[string]interface{},
	pagination *entity.Pagination,
) ([]models.K8sCrdClusterModel, uint64, error) {
	var clusterModels []models.K8sCrdClusterModel
	if err := k.db.Offset(pagination.Page).Limit(pagination.Limit).Where(params).Find(&clusterModels).Error; err != nil {
		slog.Error("List cluster models error", "error", err.Error())
		return nil, 0, err
	}
	return clusterModels, uint64(len(clusterModels)), nil
}

// NewCrdClusterDbAccess 创建 K8sCrdClusterDbAccess 接口实现实例
func NewCrdClusterDbAccess(db *gorm.DB) K8sCrdClusterDbAccess {
	return &K8sCrdClusterDbAccessImpl{db: db}
}
