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
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/gorm"
)

// K8sClusterConfigDbAccess 定义 cluster config 元数据的数据库访问接口
type K8sClusterConfigDbAccess interface {
	Create(model *models.K8sClusterConfigModel) (*models.K8sClusterConfigModel, error)
	DeleteByID(id uint64) (uint64, error)
	FindByID(id uint64) (*models.K8sClusterConfigModel, error)
	FindByClusterName(name string) (*models.K8sClusterConfigModel, error)
	Update(model *models.K8sClusterConfigModel) (uint64, error)
	ListByPage(pagination entity.Pagination) ([]models.K8sClusterConfigModel, int64, error)
	FindRegionsByParams(params *metaentity.RegionQueryParams) ([]*models.RegionModel, error)
}

// K8sClusterConfigDbAccessImpl K8sClusterConfigDbAccess 的具体实现
type K8sClusterConfigDbAccessImpl struct {
	db *gorm.DB
}

// FindRegionsByParams 根据参数查找区域列表
func (k *K8sClusterConfigDbAccessImpl) FindRegionsByParams(params *metaentity.RegionQueryParams) (
	[]*models.RegionModel,
	error,
) {
	var regions []*models.RegionModel
	if err := k.db.Model(&models.K8sClusterConfigModel{}).
		Select("is_public,region_name,region_code, provider").
		Where(params).
		Find(&regions).Limit(commconst.MaxFetchSize).Error; err != nil {
		slog.Error("find regions by params error", "param", params, "error", err)
		return nil, err
	}
	return regions, nil
}

// FindByClusterName 通过集群名称查找
func (k *K8sClusterConfigDbAccessImpl) FindByClusterName(name string) (*models.K8sClusterConfigModel, error) {
	var model models.K8sClusterConfigModel
	if err := k.db.First(&model, "cluster_name=?", name).Error; err != nil {
		slog.Error("Find model error", "error", err)
		return nil, err
	}
	return &model, nil
}

// Create 创建元数据接口实现
func (k *K8sClusterConfigDbAccessImpl) Create(model *models.K8sClusterConfigModel) (
	*models.K8sClusterConfigModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	var addedModel models.K8sClusterConfigModel
	if err := k.db.First(&addedModel, "id=?", model.ID).Error; err != nil {
		slog.Error("Find model error", "error", err)
		return nil, err
	}
	return &addedModel, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sClusterConfigDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sClusterConfigModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sClusterConfigDbAccessImpl) FindByID(id uint64) (*models.K8sClusterConfigModel, error) {
	var model models.K8sClusterConfigModel
	result := k.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	}
	return &model, nil
}

// Update 更新元数据接口实现
func (k *K8sClusterConfigDbAccessImpl) Update(model *models.K8sClusterConfigModel) (uint64, error) {
	updatedModel := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if updatedModel.Error != nil {
		slog.Error("Update model error", "error", updatedModel.Error.Error())
		return 0, updatedModel.Error
	}
	return uint64(updatedModel.RowsAffected), nil
}

// ListByPage 分页查询元数据接口实现
func (k *K8sClusterConfigDbAccessImpl) ListByPage(_ entity.Pagination) ([]models.K8sClusterConfigModel, int64, error) {
	return nil, 0, fmt.Errorf("not implemented yet")
}

// NewK8sClusterConfigDbAccess 创建 K8sClusterConfigDbAccess 接口实现实例
func NewK8sClusterConfigDbAccess(db *gorm.DB) K8sClusterConfigDbAccess {
	return &K8sClusterConfigDbAccessImpl{db: db}
}
