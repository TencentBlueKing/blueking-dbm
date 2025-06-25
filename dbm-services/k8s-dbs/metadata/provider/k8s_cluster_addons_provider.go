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

// K8sClusterAddonsProvider 定义 addon 业务逻辑层访问接口
type K8sClusterAddonsProvider interface {
	CreateClusterAddon(entity *entitys.K8sClusterAddonsEntity) (*entitys.K8sClusterAddonsEntity, error)
	DeleteClusterAddon(id uint64) (uint64, error)
	FindClusterAddonByID(id uint64) (*entitys.K8sClusterAddonsEntity, error)
	UpdateClusterAddon(entity *entitys.K8sClusterAddonsEntity) (uint64, error)
	FindClusterAddonByParams(params map[string]interface{}) ([]entitys.K8sClusterAddonsEntity, error)
}

// K8sClusterAddonsProviderImpl K8sClusterAddonsProvider 具体实现
type K8sClusterAddonsProviderImpl struct {
	kcaDbAccess dbaccess.K8sClusterAddonsDbAccess
	saDbAccess  dbaccess.K8sCrdStorageAddonDbAccess
}

// FindClusterAddonByParams 通过参数查询 cluster addon
func (k *K8sClusterAddonsProviderImpl) FindClusterAddonByParams(
	params map[string]interface{},
) ([]entitys.K8sClusterAddonsEntity, error) {
	caModels, err := k.kcaDbAccess.FindByParams(params)
	if err != nil {
		slog.Error("failed to find cluster addon by params", "error", err)
		return nil, err
	}
	var caEntities []entitys.K8sClusterAddonsEntity
	if err := copier.Copy(&caEntities, caModels); err != nil {
		slog.Error("failed to copy models", "error", err)
		return nil, err
	}

	for i, ca := range caEntities {
		saModel, err := k.saDbAccess.FindByID(ca.AddonID)
		if err != nil {
			return nil, err
		}
		saEntity := entitys.K8sCrdStorageAddonEntity{}
		if err := copier.Copy(&saEntity, saModel); err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		}
		caEntities[i].StorageAddon = saEntity
	}
	return caEntities, nil
}

// CreateClusterAddon 创建 cluster addon
func (k *K8sClusterAddonsProviderImpl) CreateClusterAddon(entity *entitys.K8sClusterAddonsEntity) (
	*entitys.K8sClusterAddonsEntity, error,
) {
	model := models.K8sClusterAddonsModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := k.kcaDbAccess.Create(&model)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := entitys.K8sClusterAddonsEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addonModel, err := k.saDbAccess.FindByID(addedEntity.AddonID)
	if err != nil {
		return nil, err
	}
	addonEntity := entitys.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(&addonEntity, addonModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedEntity.StorageAddon = addonEntity

	return &addedEntity, nil
}

// DeleteClusterAddon 删除 cluster addon
func (k *K8sClusterAddonsProviderImpl) DeleteClusterAddon(id uint64) (uint64, error) {
	return k.kcaDbAccess.DeleteByID(id)
}

// FindClusterAddonByID 查找 cluster addon
func (k *K8sClusterAddonsProviderImpl) FindClusterAddonByID(id uint64) (*entitys.K8sClusterAddonsEntity, error) {
	model, err := k.kcaDbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	entity := entitys.K8sClusterAddonsEntity{}
	if err := copier.Copy(&entity, model); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addonModel, err := k.saDbAccess.FindByID(entity.AddonID)
	if err != nil {
		return nil, err
	}
	addonEntity := entitys.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(&addonEntity, addonModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	entity.StorageAddon = addonEntity
	return &entity, nil
}

// UpdateClusterAddon 更新
func (k *K8sClusterAddonsProviderImpl) UpdateClusterAddon(entity *entitys.K8sClusterAddonsEntity) (uint64, error) {
	model := models.K8sClusterAddonsModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.kcaDbAccess.Update(&model)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sClusterAddonsProvider 创建 K8sClusterAddonsProvider 接口实现实例
func NewK8sClusterAddonsProvider(
	kcaDbAccess dbaccess.K8sClusterAddonsDbAccess,
	saDbaAccess dbaccess.K8sCrdStorageAddonDbAccess,
) K8sClusterAddonsProvider {
	return &K8sClusterAddonsProviderImpl{kcaDbAccess, saDbaAccess}
}
