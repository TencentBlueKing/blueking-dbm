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

// K8sClusterConfigProvider 定义 cluster config 业务逻辑层访问接口
type K8sClusterConfigProvider interface {
	CreateConfig(entity *entitys.K8sClusterConfigEntity) (*entitys.K8sClusterConfigEntity, error)
	DeleteConfigByID(id uint64) (uint64, error)
	FindConfigByID(id uint64) (*entitys.K8sClusterConfigEntity, error)
	FindConfigByName(name string) (*entitys.K8sClusterConfigEntity, error)
	UpdateConfig(entity *entitys.K8sClusterConfigEntity) (uint64, error)
}

// K8sClusterConfigProviderImpl K8sClusterConfigProvider 具体实现
type K8sClusterConfigProviderImpl struct {
	dbAccess dbaccess.K8sClusterConfigDbAccess
}

// CreateConfig 创建 k8s cluster config
func (k *K8sClusterConfigProviderImpl) CreateConfig(entity *entitys.K8sClusterConfigEntity) (
	*entitys.K8sClusterConfigEntity, error,
) {
	configModel := models.K8sClusterConfigModel{}
	err := copier.Copy(&configModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	createdModel, err := k.dbAccess.Create(&configModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	configEntity := entitys.K8sClusterConfigEntity{}
	if err := copier.Copy(&configEntity, createdModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &configEntity, nil
}

// DeleteConfigByID 删除 k8s cluster config
func (k *K8sClusterConfigProviderImpl) DeleteConfigByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindConfigByID 根据 ID 查找 k8s cluster config
func (k *K8sClusterConfigProviderImpl) FindConfigByID(id uint64) (*entitys.K8sClusterConfigEntity, error) {
	configModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	configEntity := entitys.K8sClusterConfigEntity{}
	if err := copier.Copy(&configEntity, configModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &configEntity, nil
}

// FindConfigByName 根据 Params 查找 k8s cluster config
func (k *K8sClusterConfigProviderImpl) FindConfigByName(name string) (*entitys.K8sClusterConfigEntity, error) {
	configModel, err := k.dbAccess.FindByClusterName(name)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	clusterEntity := entitys.K8sClusterConfigEntity{}
	if err := copier.Copy(&clusterEntity, configModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &clusterEntity, nil
}

// UpdateConfig 更新 k8s cluster config
func (k *K8sClusterConfigProviderImpl) UpdateConfig(entity *entitys.K8sClusterConfigEntity) (uint64, error) {
	configModel := models.K8sClusterConfigModel{}
	err := copier.Copy(&configModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&configModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sClusterConfigProvider 创建 K8sClusterConfigDbAccess 接口实现实例
func NewK8sClusterConfigProvider(dbAccess dbaccess.K8sClusterConfigDbAccess) K8sClusterConfigProvider {
	return &K8sClusterConfigProviderImpl{dbAccess}
}
