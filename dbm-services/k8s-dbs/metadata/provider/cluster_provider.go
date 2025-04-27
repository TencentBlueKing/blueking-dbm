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

// K8sCrdClusterProvider 定义 cluster 业务逻辑层访问接口
type K8sCrdClusterProvider interface {
	CreateCluster(entity *entitys.K8sCrdClusterEntity) (*entitys.K8sCrdClusterEntity, error)
	DeleteClusterByID(id uint64) (uint64, error)
	FindClusterByID(id uint64) (*entitys.K8sCrdClusterEntity, error)
	FindByParams(params map[string]interface{}) (*entitys.K8sCrdClusterEntity, error)
	UpdateCluster(entity *entitys.K8sCrdClusterEntity) (uint64, error)
}

// K8sCrlClusterProviderImpl K8sCrlClusterProvider 具体实现
type K8sCrlClusterProviderImpl struct {
	dbAccess dbaccess.K8sCrdClusterDbAccess
}

// CreateCluster 创建 cluster
func (k *K8sCrlClusterProviderImpl) CreateCluster(entity *entitys.K8sCrdClusterEntity) (
	*entitys.K8sCrdClusterEntity, error,
) {
	k8sCrdClusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&k8sCrdClusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	clusterModel, err := k.dbAccess.Create(&k8sCrdClusterModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	clusterEntity := entitys.K8sCrdClusterEntity{}
	if err := copier.Copy(&clusterEntity, clusterModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &clusterEntity, nil
}

// DeleteClusterByID 删除 cluster
func (k *K8sCrlClusterProviderImpl) DeleteClusterByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindClusterByID 通过 ID 查找 cluster
func (k *K8sCrlClusterProviderImpl) FindClusterByID(id uint64) (*entitys.K8sCrdClusterEntity, error) {
	clusterModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	clusterEntity := entitys.K8sCrdClusterEntity{}
	if err := copier.Copy(&clusterEntity, clusterModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &clusterEntity, nil
}

// FindByParams 通过 params 查找 cluster
func (k *K8sCrlClusterProviderImpl) FindByParams(params map[string]interface{}) (*entitys.K8sCrdClusterEntity, error) {
	clusterModel, err := k.dbAccess.FindByParams(params)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	clusterEntity := entitys.K8sCrdClusterEntity{}
	if err := copier.Copy(&clusterEntity, clusterModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &clusterEntity, nil
}

// UpdateCluster 更新 cluster
func (k *K8sCrlClusterProviderImpl) UpdateCluster(entity *entitys.K8sCrdClusterEntity) (uint64, error) {
	clusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&clusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&clusterModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdClusterProvider 创建 K8sCrdClusterProvider 接口实现实例
func NewK8sCrdClusterProvider(dbAccess dbaccess.K8sCrdClusterDbAccess) K8sCrdClusterProvider {
	return &K8sCrlClusterProviderImpl{dbAccess}
}
