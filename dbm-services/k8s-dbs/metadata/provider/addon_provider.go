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

// K8sCrdStorageAddonProvider 定义 addon 业务逻辑层访问接口
type K8sCrdStorageAddonProvider interface {
	CreateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (*entitys.K8sCrdStorageAddonEntity, error)
	DeleteStorageAddonByID(id uint64) (uint64, error)
	FindStorageAddonByID(id uint64) (*entitys.K8sCrdStorageAddonEntity, error)
	UpdateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (uint64, error)
}

// K8sCrdStorageAddonProviderImpl K8sCrdStorageAddonProvider 具体实现
type K8sCrdStorageAddonProviderImpl struct {
	dbAccess dbaccess.K8sCrdStorageAddonDbAccess
}

// CreateStorageAddon 创建 addon
func (k *K8sCrdStorageAddonProviderImpl) CreateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (
	*entitys.K8sCrdStorageAddonEntity, error,
) {
	storageAddonModel := models.K8sCrdStorageAddonModel{}
	err := copier.Copy(&storageAddonModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedStorageAddonModel, err := k.dbAccess.Create(&storageAddonModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	storageAddonEntity := entitys.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(&storageAddonEntity, addedStorageAddonModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &storageAddonEntity, nil
}

// DeleteStorageAddonByID 删除 addon
func (k *K8sCrdStorageAddonProviderImpl) DeleteStorageAddonByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindStorageAddonByID 查找 addon
func (k *K8sCrdStorageAddonProviderImpl) FindStorageAddonByID(id uint64) (*entitys.K8sCrdStorageAddonEntity, error) {
	storageAddonModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	storageAddonEntity := entitys.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(&storageAddonEntity, storageAddonModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &storageAddonEntity, nil
}

// UpdateStorageAddon 更新 addon
func (k *K8sCrdStorageAddonProviderImpl) UpdateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (uint64, error) {
	storageAddonModel := models.K8sCrdStorageAddonModel{}
	err := copier.Copy(&storageAddonModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&storageAddonModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdStorageAddonProvider 创建 K8sCrdStorageAddonDbAccess 接口实现实例
func NewK8sCrdStorageAddonProvider(dbAccess dbaccess.K8sCrdStorageAddonDbAccess) K8sCrdStorageAddonProvider {
	return &K8sCrdStorageAddonProviderImpl{dbAccess: dbAccess}
}
