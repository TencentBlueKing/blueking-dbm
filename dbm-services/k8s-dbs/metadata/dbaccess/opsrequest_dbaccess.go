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

// K8sCrdOpsRequestDbAccess 定义 opsRequest 元数据的数据库访问接口
type K8sCrdOpsRequestDbAccess interface {
	Create(model *models.K8sCrdOpsRequestModel) (*models.K8sCrdOpsRequestModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sCrdOpsRequestModel, error)
	Update(model *models.K8sCrdOpsRequestModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdOpsRequestModel, int64, error)
}

// K8sCrdOpsRequestDbAccessImpl K8sCrdOpsRequestDbAccess 的具体实现
type K8sCrdOpsRequestDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建元数据接口实现
func (k *K8sCrdOpsRequestDbAccessImpl) Create(model *models.K8sCrdOpsRequestModel) (
	*models.K8sCrdOpsRequestModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create ops error", "error", err)
		return nil, err
	}
	var addedOps models.K8sCrdOpsRequestModel
	if err := k.db.First(&addedOps, "id=?", model.ID).Error; err != nil {
		slog.Error("Find ops error", "error", err)
		return nil, err
	}
	return &addedOps, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sCrdOpsRequestDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdOpsRequestModel{}, id)
	if result.Error != nil {
		slog.Error("Delete ops error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sCrdOpsRequestDbAccessImpl) FindByID(id uint64) (*models.K8sCrdOpsRequestModel, error) {
	var ops models.K8sCrdOpsRequestModel
	result := k.db.First(&ops, id)
	if result.Error != nil {
		slog.Error("Find ops error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &ops, nil
}

// Update 更新元数据接口实现
func (k *K8sCrdOpsRequestDbAccessImpl) Update(model *models.K8sCrdOpsRequestModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update ops error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sCrdOpsRequestDbAccessImpl) ListByPage(_ utils.Pagination) (
	[]models.K8sCrdOpsRequestModel,
	int64,
	error,
) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sCrdOpsRequestDbAccess 创建 K8sCrdOpsRequestDbAccess 接口实现实例
func NewK8sCrdOpsRequestDbAccess(db *gorm.DB) K8sCrdOpsRequestDbAccess {
	return &K8sCrdOpsRequestDbAccessImpl{db: db}
}
