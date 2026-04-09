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
	"sync"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// K8sClusterServiceProvider 定义 cluster service 业务逻辑层访问接口
type K8sClusterServiceProvider interface {
	CreateClusterService(entity *metaentity.K8sClusterServiceEntity) (*metaentity.K8sClusterServiceEntity, error)
	DeleteClusterServiceByID(id uint64) (uint64, error)
	FindClusterServiceByID(id uint64) (*metaentity.K8sClusterServiceEntity, error)
	FindByClusterID(crdClusterID uint64) ([]*metaentity.K8sClusterServiceEntity, error)
	DeleteByClusterID(crdClusterID uint64) (uint64, error)
	DeleteByClusterIDAndServiceName(crdClusterID uint64, serviceName string) (uint64, error)
	UpsertClusterServices(crdClusterID uint64, entities []*metaentity.K8sClusterServiceEntity) error
	UpsertSingleService(entity *metaentity.K8sClusterServiceEntity) error
	UpdateClusterService(entity *metaentity.K8sClusterServiceEntity) (uint64, error)
	UpdateDomains(crdClusterID uint64, serviceName, domains string) (uint64, error)
	CountExternalByClusterID(crdClusterID uint64) (int64, error)
}

// K8sClusterServiceProviderImpl K8sClusterServiceProvider 具体实现
type K8sClusterServiceProviderImpl struct {
	dbAccess dbaccess.K8sClusterServiceDbAccess
}

var (
	clusterServiceInstance K8sClusterServiceProvider
	clusterServiceOnce     sync.Once
)

// GetK8sClusterServiceProvider 获取 K8sClusterServiceProvider 单例实例
func GetK8sClusterServiceProvider(dbAccess dbaccess.K8sClusterServiceDbAccess) K8sClusterServiceProvider {
	clusterServiceOnce.Do(func() {
		clusterServiceInstance = &K8sClusterServiceProviderImpl{dbAccess: dbAccess}
	})
	if clusterServiceInstance == nil {
		panic("K8sClusterServiceProvider instance is nil after initialization")
	}
	return clusterServiceInstance
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

// FindByClusterID 根据 crd_cluster_id 查找所有关联的 cluster service
func (k *K8sClusterServiceProviderImpl) FindByClusterID(
	crdClusterID uint64,
) ([]*metaentity.K8sClusterServiceEntity, error) {
	models, err := k.dbAccess.FindByClusterID(crdClusterID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find cluster services by cluster id %d", crdClusterID)
	}
	var entities []*metaentity.K8sClusterServiceEntity
	for _, m := range models {
		entity := &metaentity.K8sClusterServiceEntity{}
		if err := copier.Copy(entity, &m); err != nil {
			return nil, errors.Wrap(err, "failed to copy")
		}
		entities = append(entities, entity)
	}
	return entities, nil
}

// DeleteByClusterID 根据 crd_cluster_id 删除所有关联的 cluster service
func (k *K8sClusterServiceProviderImpl) DeleteByClusterID(crdClusterID uint64) (uint64, error) {
	return k.dbAccess.DeleteByClusterID(crdClusterID)
}

// DeleteByClusterIDAndServiceName 根据 crd_cluster_id 和 service_name 删除特定 cluster service
func (k *K8sClusterServiceProviderImpl) DeleteByClusterIDAndServiceName(
	crdClusterID uint64, serviceName string,
) (uint64, error) {
	return k.dbAccess.DeleteByClusterIDAndServiceName(crdClusterID, serviceName)
}

// UpsertClusterServices 原子性地替换指定集群的所有 service 记录
// 如果 entities 为空，不执行任何操作（避免误删已有记录）
func (k *K8sClusterServiceProviderImpl) UpsertClusterServices(
	crdClusterID uint64, entities []*metaentity.K8sClusterServiceEntity,
) error {
	if len(entities) == 0 {
		return nil
	}

	var serviceModels []*metamodel.K8sClusterServiceModel
	for _, entity := range entities {
		m := &metamodel.K8sClusterServiceModel{}
		if err := copier.Copy(m, entity); err != nil {
			return errors.Wrap(err, "failed to copy entity to model")
		}
		serviceModels = append(serviceModels, m)
	}
	return k.dbAccess.ReplaceAllByClusterID(crdClusterID, serviceModels)
}

// UpsertSingleService 原子性地更新或插入单个 service 记录
// 在事务中根据 (crd_cluster_id, service_name) 先删除再创建
func (k *K8sClusterServiceProviderImpl) UpsertSingleService(
	entity *metaentity.K8sClusterServiceEntity,
) error {
	m := &metamodel.K8sClusterServiceModel{}
	if err := copier.Copy(m, entity); err != nil {
		return errors.Wrap(err, "failed to copy entity to model")
	}
	return k.dbAccess.UpsertByClusterIDAndServiceName(m)
}

// CountExternalByClusterID 统计指定集群下拥有外部地址的 service 数量
func (k *K8sClusterServiceProviderImpl) CountExternalByClusterID(crdClusterID uint64) (int64, error) {
	return k.dbAccess.CountExternalByClusterID(crdClusterID)
}

// UpdateDomains 仅更新指定 service 的 domains 字段
func (k *K8sClusterServiceProviderImpl) UpdateDomains(
	crdClusterID uint64, serviceName, domains string,
) (uint64, error) {
	return k.dbAccess.UpdateDomainsByClusterIDAndServiceName(crdClusterID, serviceName, domains)
}
