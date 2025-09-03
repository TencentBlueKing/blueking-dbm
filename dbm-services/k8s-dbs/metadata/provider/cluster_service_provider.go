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
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// K8sClusterServiceProvider 定义 cluster service 业务逻辑层访问接口
type K8sClusterServiceProvider interface {
	CreateClusterService(entity *metaentity.K8sClusterServiceEntity) (*metaentity.K8sClusterServiceEntity, error)
	DeleteClusterServiceByID(id uint64) (uint64, error)
	FindClusterServiceByID(id uint64) (*metaentity.K8sClusterServiceEntity, error)
	UpdateClusterService(entity *metaentity.K8sClusterServiceEntity) (uint64, error)
}

// K8sClusterServiceProviderImpl K8sClusterServiceProvider 具体实现
type K8sClusterServiceProviderImpl struct {
	dbAccess dbaccess.K8sClusterServiceDbAccess
}

// CreateClusterService 创建 cluster service
func (k *K8sClusterServiceProviderImpl) CreateClusterService(entity *metaentity.K8sClusterServiceEntity) (
	*metaentity.K8sClusterServiceEntity, error,
) {
	newModel := metamodel.K8sClusterServiceModel{}
	if err := copier.Copy(&newModel, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addedModel, err := k.dbAccess.Create(&newModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create cluster service with entity: %+v", entity)
	}

	addedEntity := metaentity.K8sClusterServiceEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	return &addedEntity, nil
}

// DeleteClusterServiceByID 删除 cluster service
func (k *K8sClusterServiceProviderImpl) DeleteClusterServiceByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindClusterServiceByID 查找 cluster service
func (k *K8sClusterServiceProviderImpl) FindClusterServiceByID(id uint64) (*metaentity.K8sClusterServiceEntity, error) {
	foundModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find cluster service with id %d", id)
	}

	foundEntity := metaentity.K8sClusterServiceEntity{}
	if err = copier.Copy(&foundEntity, foundModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	return &foundEntity, nil
}

// UpdateClusterService 更新 cluster service
func (k *K8sClusterServiceProviderImpl) UpdateClusterService(entity *metaentity.K8sClusterServiceEntity) (
	uint64,
	error,
) {
	newModel := metamodel.K8sClusterServiceModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}
	rows, err := k.dbAccess.Update(&newModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update cluster service with entity: %+v", entity)
	}
	return rows, nil
}

// NewK8sClusterServiceProvider 创建 K8sClusterServiceProvider 接口实现实例
func NewK8sClusterServiceProvider(dbAccess dbaccess.K8sClusterServiceDbAccess) K8sClusterServiceProvider {
	return &K8sClusterServiceProviderImpl{dbAccess: dbAccess}
}
