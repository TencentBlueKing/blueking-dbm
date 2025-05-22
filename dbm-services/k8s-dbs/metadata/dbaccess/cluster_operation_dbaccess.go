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
	models "k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

// ClusterOperationDbAccess 定义 cluster operation 元数据的数据库访问接口
type ClusterOperationDbAccess interface {
	Create(model *models.ClusterOperationModel) (*models.ClusterOperationModel, error)
	ListByPage(pagination utils.Pagination) ([]models.ClusterOperationModel, int64, error)
}

// ClusterOperationDbAccessImpl ClusterOperationDbAccess 的具体实现
type ClusterOperationDbAccessImpl struct {
	db *gorm.DB
}

// Create 创建 cluster operation 元数据接口实现
func (c *ClusterOperationDbAccessImpl) Create(model *models.ClusterOperationModel) (
	*models.ClusterOperationModel,
	error,
) {
	if err := c.db.Create(model).Error; err != nil {
		slog.Error("Create cluster operation error", "error", err)
		return nil, err
	}
	var addedModel models.ClusterOperationModel
	if err := c.db.First(&addedModel, "addon_type = ? and addon_version= ? and operation_id= ?",
		model.AddonType, model.AddonVersion, model.OperationID).Error; err != nil {
		slog.Error("Find cluster operation error", "error", err)
		return nil, err
	}
	return &addedModel, nil
}

// ListByPage 分页查询 cluster operation 元数据接口实现
func (c *ClusterOperationDbAccessImpl) ListByPage(pagination utils.Pagination) (
	[]models.ClusterOperationModel,
	int64,
	error,
) {
	var opsModels []models.ClusterOperationModel
	if err := c.db.Offset(pagination.Page).Limit(pagination.Limit).Where("active=1").Find(&opsModels).Error; err != nil {
		slog.Error("List cluster operation error", "error", err.Error())
		return nil, 0, err
	}
	return opsModels, int64(len(opsModels)), nil
}

// NewClusterOperationDbAccess 创建 ClusterOperationDbAccess 接口实现实例
func NewClusterOperationDbAccess(db *gorm.DB) ClusterOperationDbAccess {
	return &ClusterOperationDbAccessImpl{db: db}
}
