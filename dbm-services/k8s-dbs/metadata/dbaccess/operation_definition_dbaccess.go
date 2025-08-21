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
	models "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// OperationDefinitionDbAccess 定义 operation 元数据的数据库访问接口
type OperationDefinitionDbAccess interface {
	Create(model *models.OperationDefinitionModel) (*models.OperationDefinitionModel, error)
	FindByID(id uint64) (*models.OperationDefinitionModel, error)
	ListByPage(pagination entity.Pagination) ([]models.OperationDefinitionModel, int64, error)
}

// OperationDefinitionDbAccessImpl OperationDefinitionDbAccess 的具体实现
type OperationDefinitionDbAccessImpl struct {
	db *gorm.DB
}

// FindByID 查找 operation definition 元数据接口实现
func (o *OperationDefinitionDbAccessImpl) FindByID(id uint64) (*models.OperationDefinitionModel, error) {
	var opDefModel models.OperationDefinitionModel
	result := o.db.First(&opDefModel, id)
	if result.Error != nil {
		slog.Error("Find operation definition error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &opDefModel, nil
}

// Create 创建 operation definition 元数据接口实现
func (o *OperationDefinitionDbAccessImpl) Create(model *models.OperationDefinitionModel) (
	*models.OperationDefinitionModel,
	error,
) {
	if err := o.db.Create(model).Error; err != nil {
		slog.Error("Create operation definition error", "error", err)
		return nil, err
	}
	return model, nil
}

// ListByPage 分页查询 operation definition 元数据接口实现
func (o *OperationDefinitionDbAccessImpl) ListByPage(pagination entity.Pagination) (
	[]models.OperationDefinitionModel,
	int64,
	error,
) {
	var opDefModels []models.OperationDefinitionModel
	if err := o.db.Offset(pagination.Page).Limit(pagination.Limit).Where("active=1").Find(&opDefModels).Error; err != nil {
		slog.Error("List operation definition error", "error", err.Error())
		return nil, 0, err
	}
	return opDefModels, int64(len(opDefModels)), nil
}

// NewOperationDefinitionDbAccess 创建 OperationDefinitionDbAccess 接口实现实例
func NewOperationDefinitionDbAccess(db *gorm.DB) OperationDefinitionDbAccess {
	return &OperationDefinitionDbAccessImpl{db: db}
}
