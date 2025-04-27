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

package provider

import (
	"k8s-dbs/metadata/dbaccess"
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

// ClusterRequestRecordProvider 定义 request record 业务逻辑层访问接口
type ClusterRequestRecordProvider interface {
	CreateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (*entitys.ClusterRequestRecordEntity, error)
	DeleteRequestRecordByID(id uint64) (uint64, error)
	FindRequestRecordByID(id uint64) (*entitys.ClusterRequestRecordEntity, error)
	UpdateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (uint64, error)
}

// ClusterRequestRecordProviderImpl ClusterRequestRecordProvider 具体实现
type ClusterRequestRecordProviderImpl struct {
	dbAccess dbaccess.ClusterRequestRecordDbAccess
}

// CreateRequestRecord 创建 request record
func (k *ClusterRequestRecordProviderImpl) CreateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (
	*entitys.ClusterRequestRecordEntity, error,
) {
	newModel := models.ClusterRequestRecordModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := k.dbAccess.Create(&newModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.ClusterRequestRecordEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// DeleteRequestRecordByID 删除 addon
func (k *ClusterRequestRecordProviderImpl) DeleteRequestRecordByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindRequestRecordByID 查找 cluster
func (k *ClusterRequestRecordProviderImpl) FindRequestRecordByID(id uint64) (
	*entitys.ClusterRequestRecordEntity, error,
) {
	foundModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	foundEntity := entitys.ClusterRequestRecordEntity{}
	if err := copier.Copy(&foundEntity, foundModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &foundEntity, nil
}

// UpdateRequestRecord 更新 cluster
func (k *ClusterRequestRecordProviderImpl) UpdateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (
	uint64, error,
) {
	newModel := models.ClusterRequestRecordModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&newModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewClusterRequestRecordProvider 创建 ClusterRequestRecordProvider 接口实现实例
func NewClusterRequestRecordProvider(dbAccess dbaccess.ClusterRequestRecordDbAccess) ClusterRequestRecordProvider {
	return &ClusterRequestRecordProviderImpl{dbAccess: dbAccess}
}
