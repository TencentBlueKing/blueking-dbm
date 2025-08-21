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

// ComponentOperationDbAccess 定义 component operation 元数据的数据库访问接口
type ComponentOperationDbAccess interface {
	Create(model *models.ComponentOperationModel) (*models.ComponentOperationModel, error)
	ListByPage(pagination entity.Pagination) ([]models.ComponentOperationModel, int64, error)
}

// ComponentOperationDbAccessImpl ComponentOperationDbAccess 的具体实现
type ComponentOperationDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 cluster operation 元数据接口实现
func (c *ComponentOperationDbAccessImpl) Create(model *models.ComponentOperationModel) (
	*models.ComponentOperationModel,
	error,
) {
	if err := c.db.Create(model).Error; err != nil {
		slog.Error("Create component operation error", "error", err)
		return nil, err
	}
	return model, nil
}

// ListByPage 分页查询 component operation 元数据接口实现
func (c *ComponentOperationDbAccessImpl) ListByPage(pagination entity.Pagination) (
	[]models.ComponentOperationModel,
	int64,
	error,
) {
	var cmpOpsDefModels []models.ComponentOperationModel
	if err := c.db.
		Offset(pagination.Page).
		Limit(pagination.Limit).
		Where("active=1").Find(&cmpOpsDefModels).Error; err != nil {
		slog.Error("List component operation error", "error", err.Error())
		return nil, 0, err
	}
	return cmpOpsDefModels, int64(len(cmpOpsDefModels)), nil
}

// NewComponentOperationDbAccess 创建 ComponentOperationDbAccess 接口实现实例
func NewComponentOperationDbAccess(db *gorm.DB) ComponentOperationDbAccess {
	return &ComponentOperationDbAccessImpl{db: db}
}
