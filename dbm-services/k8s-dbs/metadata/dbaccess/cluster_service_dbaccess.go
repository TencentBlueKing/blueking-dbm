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
	"sync"

	"github.com/pkg/errors"

	"gorm.io/gorm"
)

// K8sClusterServiceDbAccess 定义 cluster service 元数据的数据库访问接口
type K8sClusterServiceDbAccess interface {
	Create(model *models.K8sClusterServiceModel) (*models.K8sClusterServiceModel, error)
	DeleteByID(id uint64) (uint64, error)
	DeleteByClusterID(crdClusterID uint64) (uint64, error)
	DeleteByClusterIDAndServiceName(crdClusterID uint64, serviceName string) (uint64, error)
	FindByID(id uint64) (*models.K8sClusterServiceModel, error)
	FindByClusterID(crdClusterID uint64) ([]models.K8sClusterServiceModel, error)
	Update(model *models.K8sClusterServiceModel) (uint64, error)
	ListByPage(pagination entity.Pagination) ([]models.K8sClusterServiceModel, int64, error)
	ReplaceAllByClusterID(crdClusterID uint64, serviceModels []*models.K8sClusterServiceModel) error
	UpsertByClusterIDAndServiceName(model *models.K8sClusterServiceModel) error
	UpdateDomainsByClusterIDAndServiceName(crdClusterID uint64, serviceName, domains string) (uint64, error)
	CountExternalByClusterID(crdClusterID uint64) (int64, error)
}

// K8sClusterServiceDbAccessImpl K8sClusterServiceDbAccess 的具体实现
type K8sClusterServiceDbAccessImpl struct {
	db *gorm.DB
}

var (
	serviceInstance K8sClusterServiceDbAccess
	serviceOnce     sync.Once
)

// GetClusterServiceDbAccess 获取 K8sClusterServiceDbAccess 单例实例
func GetClusterServiceDbAccess(db *gorm.DB) K8sClusterServiceDbAccess {
	serviceOnce.Do(func() {
		serviceInstance = &K8sClusterServiceDbAccessImpl{db: db}
	})
	if serviceInstance == nil {
		panic("K8sClusterServiceDbAccess instance is nil after initialization")
	}
	return serviceInstance
}

// Create 创建元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) Create(model *models.K8sClusterServiceModel) (
	*models.K8sClusterServiceModel, error,
) {
	if err := k.db.Create(model).Error; err != nil {
		return nil, errors.Wrapf(err, "failed to create cluster service with model: %+v", model)
	}
	return model, nil
}

// DeleteByID 删除元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) DeleteByID(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sClusterServiceModel{}, id)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete cluster service with id %d", id)
	}
	return uint64(result.RowsAffected), nil
}

// FindByID 查找元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) FindByID(id uint64) (*models.K8sClusterServiceModel, error) {
	var request models.K8sClusterServiceModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find cluster service with id %d", id)
	}
	return &request, nil
}

// Update 更新元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) Update(model *models.K8sClusterServiceModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to update cluster service with model: %+v", model)
	}
	return uint64(result.RowsAffected), nil
}

// ReplaceAllByClusterID 原子性地替换指定集群的所有 service 记录
// 在事务中先删除旧记录，再批量插入新记录
func (k *K8sClusterServiceDbAccessImpl) ReplaceAllByClusterID(
	crdClusterID uint64, serviceModels []*models.K8sClusterServiceModel,
) error {
	return k.db.Transaction(func(tx *gorm.DB) error {
		result := tx.Where("crd_cluster_id = ?", crdClusterID).Delete(&models.K8sClusterServiceModel{})
		if result.Error != nil {
			return errors.Wrapf(result.Error, "failed to delete old cluster services for cluster id %d", crdClusterID)
		}
		if len(serviceModels) == 0 {
			return nil
		}
		if err := tx.Create(serviceModels).Error; err != nil {
			return errors.Wrapf(err, "failed to batch create cluster services for cluster id %d", crdClusterID)
		}
		return nil
	})
}

// DeleteByClusterID 根据 crd_cluster_id 删除所有关联的 cluster service 记录
func (k *K8sClusterServiceDbAccessImpl) DeleteByClusterID(crdClusterID uint64) (uint64, error) {
	result := k.db.Where("crd_cluster_id = ?", crdClusterID).Delete(&models.K8sClusterServiceModel{})
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error, "failed to delete cluster services by cluster id %d", crdClusterID)
	}
	return uint64(result.RowsAffected), nil
}

// DeleteByClusterIDAndServiceName 根据 crd_cluster_id 和 service_name 删除特定 cluster service 记录
func (k *K8sClusterServiceDbAccessImpl) DeleteByClusterIDAndServiceName(
	crdClusterID uint64, serviceName string,
) (uint64, error) {
	result := k.db.Where("crd_cluster_id = ? AND service_name = ?", crdClusterID, serviceName).
		Delete(&models.K8sClusterServiceModel{})
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error,
			"failed to delete cluster service by cluster id %d and service name %s", crdClusterID, serviceName)
	}
	return uint64(result.RowsAffected), nil
}

// FindByClusterID 根据 crd_cluster_id 查询所有关联的 cluster service 记录
func (k *K8sClusterServiceDbAccessImpl) FindByClusterID(crdClusterID uint64) ([]models.K8sClusterServiceModel, error) {
	var services []models.K8sClusterServiceModel
	result := k.db.Where("crd_cluster_id = ?", crdClusterID).Find(&services)
	if result.Error != nil {
		return nil, errors.Wrapf(result.Error, "failed to find cluster services by cluster id %d", crdClusterID)
	}
	return services, nil
}

// UpsertByClusterIDAndServiceName 原子性地更新或插入单个 service 记录
// 先查询是否存在：不存在则 INSERT；存在且数据有变化则 UPDATE；无变化则跳过
func (k *K8sClusterServiceDbAccessImpl) UpsertByClusterIDAndServiceName(
	model *models.K8sClusterServiceModel,
) error {
	return k.db.Transaction(func(tx *gorm.DB) error {
		var existing models.K8sClusterServiceModel
		err := tx.Where("crd_cluster_id = ? AND service_name = ?", model.CrdClusterID, model.ServiceName).
			First(&existing).Error
		if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
			return errors.Wrapf(err,
				"failed to query existing service: cluster_id=%d, service=%s",
				model.CrdClusterID, model.ServiceName)
		}

		if errors.Is(err, gorm.ErrRecordNotFound) {
			// 记录不存在，插入新记录
			if createErr := tx.Create(model).Error; createErr != nil {
				return errors.Wrapf(createErr,
					"failed to create service for upsert: cluster_id=%d, service=%s",
					model.CrdClusterID, model.ServiceName)
			}
			return nil
		}

		// 记录已存在，检查数据是否有变化
		if serviceDataEqual(&existing, model) {
			return nil
		}

		// 数据有变化，更新记录，保留 created_at 和 created_by
		model.ID = existing.ID
		// 如果新记录未设置 extra，保留已有的 extra 值
		if model.Extra == "" && existing.Extra != "" {
			model.Extra = existing.Extra
		}
		// domains 的权威源来自 DBM API 创建成功后的回写，
		// informer 重复触发时未携带 domains，需保留已有值避免被清空
		if model.Domains == "" && existing.Domains != "" {
			model.Domains = existing.Domains
		}
		if updateErr := tx.Model(&models.K8sClusterServiceModel{}).
			Where("id = ?", existing.ID).
			Select("*").
			Omit("ID", "CreatedAt", "CreatedBy").
			Updates(model).Error; updateErr != nil {
			return errors.Wrapf(updateErr,
				"failed to update service for upsert: cluster_id=%d, service=%s",
				model.CrdClusterID, model.ServiceName)
		}
		return nil
	})
}

// UpdateDomainsByClusterIDAndServiceName 仅更新指定 service 的 domains 字段
// 用于 DBM API 创建域名成功后回写本地记录，避免读旧 entity 去 upsert 产生覆盖
func (k *K8sClusterServiceDbAccessImpl) UpdateDomainsByClusterIDAndServiceName(
	crdClusterID uint64, serviceName, domains string,
) (uint64, error) {
	result := k.db.Model(&models.K8sClusterServiceModel{}).
		Where("crd_cluster_id = ? AND service_name = ?", crdClusterID, serviceName).
		Update("domains", domains)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error,
			"failed to update domains: cluster_id=%d, service=%s", crdClusterID, serviceName)
	}
	return uint64(result.RowsAffected), nil
}

// serviceDataEqual 比较两条 service 记录的业务字段是否一致
func serviceDataEqual(a, b *models.K8sClusterServiceModel) bool {
	return a.ComponentName == b.ComponentName &&
		a.ServiceType == b.ServiceType &&
		a.Annotations == b.Annotations &&
		a.InternalAddrs == b.InternalAddrs &&
		a.ExternalAddrs == b.ExternalAddrs &&
		a.Domains == b.Domains &&
		a.Extra == b.Extra &&
		a.Description == b.Description
}

// ListByPage 分页查询元数据接口实现
func (k *K8sClusterServiceDbAccessImpl) ListByPage(_ entity.Pagination) (
	[]models.K8sClusterServiceModel,
	int64,
	error,
) {
	return nil, 0, errors.New("not implemented")
}

// CountExternalByClusterID 统计指定集群下拥有外部地址的 service 数量
func (k *K8sClusterServiceDbAccessImpl) CountExternalByClusterID(crdClusterID uint64) (int64, error) {
	var count int64
	result := k.db.Model(&models.K8sClusterServiceModel{}).
		Where("crd_cluster_id = ? AND external_addrs IS NOT NULL AND external_addrs != ''", crdClusterID).
		Count(&count)
	if result.Error != nil {
		return 0, errors.Wrapf(result.Error,
			"failed to count external services by cluster id %d", crdClusterID)
	}
	return count, nil
}
