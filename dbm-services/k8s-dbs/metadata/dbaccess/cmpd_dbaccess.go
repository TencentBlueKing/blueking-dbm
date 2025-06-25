/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use k file except in compliance with the License.

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
	"k8s-dbs/common/entity"
	models "k8s-dbs/metadata/dbaccess/model"
	"log/slog"

	"gorm.io/gorm"
)

// K8sCrdCmpdDbAccess 定义 cmpd 元数据的数据库访问接口
type K8sCrdCmpdDbAccess interface {
	Create(model *models.K8sCrdComponentDefinitionModel) (*models.K8sCrdComponentDefinitionModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdComponentDefinitionModel, error)
	Update(model *models.K8sCrdComponentDefinitionModel) (uint64, error)
	ListByPage(pagination entity.Pagination) ([]models.K8sCrdComponentDefinitionModel, int64, error)
}

// K8sCrdComponentDefinitionDbAccessImpl K8sCrdCmpdDbAccess 的具体实现
type K8sCrdComponentDefinitionDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *K8sCrdComponentDefinitionDbAccessImpl) Create(cmpd *models.K8sCrdComponentDefinitionModel) (
	*models.K8sCrdComponentDefinitionModel, error,
) {
	if err := k.db.Create(cmpd).Error; err != nil {
		slog.Error("Create componentdefinition error", "error", err)
		return nil, err
	}
	var addedComponentDefinition models.K8sCrdComponentDefinitionModel
	if err := k.db.First(&addedComponentDefinition, "componentdefinition_name=?",
		cmpd.ComponentDefinitionName).Error; err != nil {
		slog.Error("Find componentdefinition error", "error", err)
		return nil, err
	}
	return &addedComponentDefinition, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sCrdComponentDefinitionDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdComponentDefinitionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete componentdefinition error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sCrdComponentDefinitionDbAccessImpl) FindByID(id uint64) (*models.K8sCrdComponentDefinitionModel, error) {
	var componentDefinition models.K8sCrdComponentDefinitionModel
	result := k.db.First(&componentDefinition, id)
	if result.Error != nil {
		slog.Error("Find componentdefinition error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &componentDefinition, nil
}

// Update 更新元数据接口实现
func (k *K8sCrdComponentDefinitionDbAccessImpl) Update(cmpd *models.K8sCrdComponentDefinitionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(cmpd)
	if result.Error != nil {
		slog.Error("Update componentdefinition error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sCrdComponentDefinitionDbAccessImpl) ListByPage(_ entity.Pagination) (
	[]models.K8sCrdComponentDefinitionModel,
	int64,
	error,
) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sCrdCmpdDbAccess 创建 K8sCrdCmpdDbAccess 接口实现实例
func NewK8sCrdCmpdDbAccess(db *gorm.DB) K8sCrdCmpdDbAccess {
	return &K8sCrdComponentDefinitionDbAccessImpl{db: db}
}
