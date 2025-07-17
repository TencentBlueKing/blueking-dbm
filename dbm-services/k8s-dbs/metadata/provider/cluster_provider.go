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
	"context"
	"k8s-dbs/common/entity"
	corehelper "k8s-dbs/common/helper"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/metadata/dbaccess"
	metaentity "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"log/slog"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"github.com/jinzhu/copier"
)

// K8sCrdClusterProvider 定义 cluster 业务逻辑层访问接口
type K8sCrdClusterProvider interface {
	CreateCluster(entity *metaentity.K8sCrdClusterEntity) (*metaentity.K8sCrdClusterEntity, error)
	DeleteClusterByID(id uint64) (uint64, error)
	FindClusterByID(id uint64) (*metaentity.K8sCrdClusterEntity, error)
	FindByParams(params *metaentity.ClusterQueryParams) (*metaentity.K8sCrdClusterEntity, error)
	UpdateCluster(entity *metaentity.K8sCrdClusterEntity) (uint64, error)
	ListClusters(params *metaentity.ClusterQueryParams,
		pagination *entity.Pagination,
	) ([]*metaentity.K8sCrdClusterEntity, uint64, error)
}

// K8sCrlClusterProviderImpl K8sCrlClusterProvider 具体实现
type K8sCrlClusterProviderImpl struct {
	clusterDbAccess          dbaccess.K8sCrdClusterDbAccess
	addonDbAccess            dbaccess.K8sCrdStorageAddonDbAccess
	clusterTagDbAccess       dbaccess.K8sCrdClusterTagDbAccess
	k8sClusterConfigDbAccess dbaccess.K8sClusterConfigDbAccess
}

// CreateCluster 创建 cluster
func (k *K8sCrlClusterProviderImpl) CreateCluster(entity *metaentity.K8sCrdClusterEntity) (
	*metaentity.K8sCrdClusterEntity, error,
) {
	k8sCrdClusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&k8sCrdClusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	clusterModel, err := k.clusterDbAccess.Create(&k8sCrdClusterModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	clusterEntity := metaentity.K8sCrdClusterEntity{}
	if err := copier.Copy(&clusterEntity, clusterModel); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	return &clusterEntity, nil
}

// DeleteClusterByID 删除 cluster
func (k *K8sCrlClusterProviderImpl) DeleteClusterByID(id uint64) (uint64, error) {
	return k.clusterDbAccess.DeleteByID(id)
}

// FindClusterByID 通过 ID 查找 cluster
func (k *K8sCrlClusterProviderImpl) FindClusterByID(id uint64) (*metaentity.K8sCrdClusterEntity, error) {
	clusterModel, err := k.clusterDbAccess.FindByID(id)
	if err != nil {
		return nil, err
	}
	clusterEntity := &metaentity.K8sCrdClusterEntity{}
	if err := copier.Copy(clusterEntity, clusterModel); err != nil {
		return nil, err
	}

	addonModel, err := k.addonDbAccess.FindByID(clusterEntity.AddonID)
	if err != nil {
		return nil, err
	}
	addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(addonEntity, addonModel); err != nil {
		return nil, err
	}
	clusterEntity.AddonInfo = addonEntity

	tagModels, err := k.clusterTagDbAccess.FindByClusterID(clusterEntity.ID)
	if err != nil {
		return nil, err
	}
	var tagEntities []*metaentity.K8sCrdClusterTagEntity
	if err := copier.Copy(&tagEntities, tagModels); err != nil {
		return nil, err
	}
	clusterEntity.Tags = tagEntities

	k8sConfigModel, err := k.k8sClusterConfigDbAccess.FindByID(clusterEntity.K8sClusterConfigID)
	if err != nil {
		return nil, err
	}
	k8sConfigEntity := &metaentity.K8sClusterConfigEntity{}
	if err := copier.Copy(k8sConfigEntity, k8sConfigModel); err != nil {
		return nil, err
	}
	clusterEntity.K8sClusterConfig = k8sConfigEntity

	clusterResource, err := k.getClusterResource(clusterEntity)
	if err != nil {
		slog.Warn("Failed to get cluster resource", "error", err)
	} else {
		clusterEntity.Status = string(clusterResource.ClusterStatus.Phase)
	}
	return clusterEntity, nil
}

// FindByParams 通过 params 查找 cluster
func (k *K8sCrlClusterProviderImpl) FindByParams(params *metaentity.ClusterQueryParams) (
	*metaentity.K8sCrdClusterEntity,
	error,
) {
	clusterModel, err := k.clusterDbAccess.FindByParams(params)
	if err != nil {
		slog.Error("Failed to find clusterModel by params", "params", params, "error", err)
		return nil, err
	}
	clusterEntity := metaentity.K8sCrdClusterEntity{}
	if err := copier.Copy(&clusterEntity, clusterModel); err != nil {
		return nil, err
	}
	addonModel, err := k.addonDbAccess.FindByID(clusterModel.AddonID)
	if err != nil {
		slog.Error("Failed to find addonModel by ID", "ID", clusterModel.AddonID, "error", err)
		return nil, err
	}
	addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
	if err := copier.Copy(addonEntity, addonModel); err != nil {
		return nil, err
	}
	clusterEntity.AddonInfo = addonEntity
	return &clusterEntity, nil
}

// UpdateCluster 更新 cluster
func (k *K8sCrlClusterProviderImpl) UpdateCluster(entity *metaentity.K8sCrdClusterEntity) (uint64, error) {
	clusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&clusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.clusterDbAccess.Update(&clusterModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// ListClusters 查询 cluster 列表
func (k *K8sCrlClusterProviderImpl) ListClusters(
	params *metaentity.ClusterQueryParams,
	pagination *entity.Pagination,
) ([]*metaentity.K8sCrdClusterEntity, uint64, error) {
	clusterModels, count, err := k.clusterDbAccess.ListByPage(params, pagination)
	if err != nil {
		slog.Error("Failed to list cluster", "error", err)
		return nil, 0, err
	}
	var clusterEntities []*metaentity.K8sCrdClusterEntity
	if err := copier.Copy(&clusterEntities, clusterModels); err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, 0, err
	}
	for _, clusterEntity := range clusterEntities {
		addonModel, err := k.addonDbAccess.FindByID(clusterEntity.AddonID)
		if err != nil {
			slog.Warn("Failed to find addonModel by ID", "ID", clusterEntity.AddonID, "error", err)
			continue
		}
		addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
		if err := copier.Copy(addonEntity, addonModel); err != nil {
			slog.Warn("Failed to copy model to copied model", "error", err)
			continue
		}
		clusterEntity.AddonInfo = addonEntity
		clusterResource, err := k.getClusterResource(clusterEntity)
		if err != nil {
			slog.Warn("Failed to get cluster resource", "error", err)
			continue
		}
		clusterEntity.Status = string(clusterResource.ClusterStatus.Phase)
	}
	return clusterEntities, count, nil
}

// getClusterResource 获取 cluster 资源对象
func (k *K8sCrlClusterProviderImpl) getClusterResource(
	clusterEntity *metaentity.K8sCrdClusterEntity,
) (*coreentity.ClusterResponseData, error) {
	k8sClusterConfigModel, err := k.k8sClusterConfigDbAccess.FindByID(clusterEntity.K8sClusterConfigID)
	if err != nil {
		slog.Warn("Failed to find k8sCluster by ID", "ID", clusterEntity.K8sClusterConfigID, "error", err)
		return nil, err
	}
	k8sClusterConfigEntity := &metaentity.K8sClusterConfigEntity{}
	if err := copier.Copy(k8sClusterConfigEntity, k8sClusterConfigModel); err != nil {
		slog.Warn("Failed to copy k8sClusterConfigModel to k8sClusterConfigEntity", "error", err)
		return nil, err
	}
	k8sClient, err := corehelper.NewK8sClient(k8sClusterConfigEntity)
	if err != nil {
		slog.Warn("Failed to create k8sClient", "error", err)
		return nil, err
	}
	clusterUnStructured, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(clusterEntity.Namespace).
		Get(context.TODO(), clusterEntity.ClusterName, metav1.GetOptions{})
	if err != nil {
		slog.Warn("Failed to get cluster resource", "error", err)
		return nil, err
	}
	clusterResource, err := coreentity.GetClusterResponseData(clusterUnStructured)
	if err != nil {
		slog.Warn("Failed to get cluster resource from k8s api server", "error", err)
		return nil, err
	}
	return clusterResource, nil
}

// NewK8sCrdClusterProvider 创建 K8sCrdClusterProvider 接口实现实例
func NewK8sCrdClusterProvider(
	clusterDbAccess dbaccess.K8sCrdClusterDbAccess,
	addonDbAccess dbaccess.K8sCrdStorageAddonDbAccess,
	clusterTagDbAccess dbaccess.K8sCrdClusterTagDbAccess,
	k8sClusterConfigDbaccess dbaccess.K8sClusterConfigDbAccess,
) K8sCrdClusterProvider {
	return &K8sCrlClusterProviderImpl{
		clusterDbAccess:          clusterDbAccess,
		addonDbAccess:            addonDbAccess,
		clusterTagDbAccess:       clusterTagDbAccess,
		k8sClusterConfigDbAccess: k8sClusterConfigDbaccess,
	}
}
