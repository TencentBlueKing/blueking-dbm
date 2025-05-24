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

// K8sCrdClusterDefinitionDbAccess 定义 cd 元数据的数据库访问接口
type K8sCrdClusterDefinitionDbAccess interface {
	Create(model *models.K8sCrdClusterDefinitionModel) (*models.K8sCrdClusterDefinitionModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdClusterDefinitionModel, error)
	Update(model *models.K8sCrdClusterDefinitionModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdClusterDefinitionModel, int64, error)
}

// K8sCrdClusterDefinitionDbAccessImpl K8sCrdClusterDefinitionDbAccess 的具体实现
type K8sCrdClusterDefinitionDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 cd 元数据接口实现
func (k *K8sCrdClusterDefinitionDbAccessImpl) Create(model *models.K8sCrdClusterDefinitionModel) (
	*models.K8sCrdClusterDefinitionModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create clusterdefinition error", "error", err)
		return nil, err
	}
	var created models.K8sCrdClusterDefinitionModel
	if err := k.db.First(&created, "clusterdefinition_name = ?", model.ClusterDefinitionName).Error; err != nil {
		slog.Error("Find clusterdefinition error", "error", err)
		return nil, err
	}
	return &created, nil
}

// DeleteByID 删除 cd 元数据接口实现
func (k *K8sCrdClusterDefinitionDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterDefinitionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete clusterdefinition error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找 cd 元数据接口实现
func (k *K8sCrdClusterDefinitionDbAccessImpl) FindByID(id uint64) (*models.K8sCrdClusterDefinitionModel, error) {
	var clusterDefModel models.K8sCrdClusterDefinitionModel
	result := k.db.First(&clusterDefModel, id)
	if result.Error != nil {
		slog.Error("Find clusterdefinition error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &clusterDefModel, nil
}

// Update 更新 cd 元数据接口实现
func (k *K8sCrdClusterDefinitionDbAccessImpl) Update(model *models.K8sCrdClusterDefinitionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update clusterdefinition error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询 cd 元数据接口实现
func (k *K8sCrdClusterDefinitionDbAccessImpl) ListByPage(_ utils.Pagination) (
	[]models.K8sCrdClusterDefinitionModel,
	int64,
	error,
) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sCrdClusterDefinitionDbAccess 创建 K8sCrdClusterDefinitionDbAccess 接口实现实例
func NewK8sCrdClusterDefinitionDbAccess(db *gorm.DB) K8sCrdClusterDefinitionDbAccess {
	return &K8sCrdClusterDefinitionDbAccessImpl{db: db}
}
