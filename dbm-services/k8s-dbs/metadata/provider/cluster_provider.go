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
	"encoding/json"
	"k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	"k8s-dbs/metadata/dbaccess"
	metaentity "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"log/slog"

	"github.com/pkg/errors"

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
	FindClusterTopology(id uint64) (*metaentity.ClusterTopologyEntity, error)
}

// K8sCrdClusterProviderImpl K8sCrlClusterProvider 具体实现
type K8sCrdClusterProviderImpl struct {
	clusterDbAccess          dbaccess.K8sCrdClusterDbAccess
	addonDbAccess            dbaccess.K8sCrdStorageAddonDbAccess
	clusterTagDbAccess       dbaccess.K8sCrdClusterTagDbAccess
	k8sClusterConfigDbAccess dbaccess.K8sClusterConfigDbAccess
	addonTopologyDbAccess    dbaccess.AddonTopologyDbAccess
}

// K8sCrdClusterProviderOptions K8sCrdClusterProvider 函数选项
type K8sCrdClusterProviderOptions func(*K8sCrdClusterProviderImpl)

// K8sCrdClusterProviderBuilder 辅助构建结构体
type K8sCrdClusterProviderBuilder struct{}

// WithClusterDbAccess 设置 K8sCrdClusterDbAccess
func (k *K8sCrdClusterProviderBuilder) WithClusterDbAccess(
	access dbaccess.K8sCrdClusterDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.clusterDbAccess = access
	}
}

// WithAddonDbAccess 设置 K8sCrdStorageAddonDbAccess
func (k *K8sCrdClusterProviderBuilder) WithAddonDbAccess(
	access dbaccess.K8sCrdStorageAddonDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.addonDbAccess = access
	}
}

// WithClusterTagDbAccess 设置 K8sCrdClusterTagDbAccess
func (k *K8sCrdClusterProviderBuilder) WithClusterTagDbAccess(
	access dbaccess.K8sCrdClusterTagDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.clusterTagDbAccess = access
	}
}

// WithK8sClusterConfigDbAccess 设置 K8sClusterConfigDbAccess
func (k *K8sCrdClusterProviderBuilder) WithK8sClusterConfigDbAccess(
	access dbaccess.K8sClusterConfigDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.k8sClusterConfigDbAccess = access
	}
}

// WithAddonTopologyDbAccess 设置 AddonTopologyDbAccess
func (k *K8sCrdClusterProviderBuilder) WithAddonTopologyDbAccess(
	access dbaccess.AddonTopologyDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.addonTopologyDbAccess = access
	}
}

// FindClusterTopology 获取集群拓扑详情
func (k *K8sCrdClusterProviderImpl) FindClusterTopology(id uint64) (*metaentity.ClusterTopologyEntity, error) {
	cluster, err := k.FindClusterByID(id)
	if err != nil {
		return nil, err
	}
	var clusterTopology metaentity.ClusterTopologyEntity
	err = copier.Copy(&clusterTopology, cluster)
	if err != nil {
		return nil, err
	}
	addonType := cluster.AddonInfo.AddonType
	addonCategory := cluster.AddonInfo.AddonCategory
	addonVersion := cluster.AddonInfo.AddonVersion
	addonName := cluster.AddonInfo.AddonName
	topoName := cluster.TopoName
	clusterTopology.AddonName = addonName
	clusterTopology.AddonVersion = addonVersion
	clusterTopology.AddonCategory = addonCategory
	clusterTopology.AddonType = addonType
	clusterTopology.K8sClusterName = cluster.K8sClusterConfig.ClusterName
	// 获取集群 Topology 静态配置
	topoParams := &metaentity.AddonTopologyQueryParams{
		AddonType:     addonType,
		AddonCategory: addonCategory,
		AddonVersion:  addonVersion,
		TopologyName:  topoName,
	}
	addonTopoArray, err := k.addonTopologyDbAccess.FindByParams(topoParams)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find cluster topology with params %+v", topoParams)
	}
	if len(addonTopoArray) > 0 {
		err = k.setClusterTopology(addonTopoArray, &clusterTopology)
		if err != nil {
			return nil, errors.Wrapf(err, "failed to set cluster topology with params %+v", topoParams)
		}
	}
	return &clusterTopology, nil
}

// SetClusterTopology 渲染 cluster 的 topology
func (k *K8sCrdClusterProviderImpl) setClusterTopology(
	addonTopoArray []*models.AddonTopologyModel,
	clusterTopology *metaentity.ClusterTopologyEntity,
) error {
	addonTopo := addonTopoArray[0]
	relationsStr := addonTopo.Relations
	componentsStr := addonTopo.Components
	clusterTopology.Description = addonTopo.Description
	err := json.Unmarshal([]byte(relationsStr), &clusterTopology.Relations)
	if err != nil {
		return errors.Wrapf(err, "unmarshal relations error. relation is: %s", relationsStr)
	}
	err = json.Unmarshal([]byte(componentsStr), &clusterTopology.Components)
	if err != nil {
		return errors.Wrapf(err, "unmarshal components error. components is: %s", componentsStr)
	}
	k8sClusterConfig, err := k.k8sClusterConfigDbAccess.FindByClusterName(clusterTopology.K8sClusterName)
	if err != nil {
		return errors.Wrapf(err, "failed to find k8s cluster config by cluster name %s",
			clusterTopology.K8sClusterName)
	}
	var k8sClusterConfigEntity metaentity.K8sClusterConfigEntity
	if err = copier.Copy(&k8sClusterConfigEntity, k8sClusterConfig); err != nil {
		return errors.Wrap(err, "failed to copy")
	}
	k8sClient, err := commutil.NewK8sClient(&k8sClusterConfigEntity)
	if err != nil {
		return errors.Wrap(err, "failed to create k8s client")
	}
	// 获取 component instances
	for i, component := range clusterTopology.Components {
		componentQueryParams := &coreentity.ComponentQueryParams{
			ClusterName:   clusterTopology.ClusterName,
			ComponentName: component.Name,
		}
		pods, err := coreutil.GetComponentPods(addonTopo.AddonType, componentQueryParams, k8sClient)
		if err != nil {
			return errors.Wrapf(err, "failed to find pods for component with params: %+v", componentQueryParams)
		}
		if len(pods) > 0 {
			var componentPodEntities []*metaentity.ComponentPodEntity
			if err := copier.Copy(&componentPodEntities, pods); err != nil {
				return errors.Wrap(err, "failed to copy")
			}
			clusterTopology.Components[i].Instances = componentPodEntities
		}
	}
	return nil
}

// CreateCluster 创建 cluster
func (k *K8sCrdClusterProviderImpl) CreateCluster(entity *metaentity.K8sCrdClusterEntity) (
	*metaentity.K8sCrdClusterEntity, error,
) {
	k8sCrdClusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&k8sCrdClusterModel, entity)
	if err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	clusterModel, err := k.clusterDbAccess.Create(&k8sCrdClusterModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create cluster with entity: %+v", entity)
	}
	clusterEntity := metaentity.K8sCrdClusterEntity{}
	if err = copier.Copy(&clusterEntity, clusterModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &clusterEntity, nil
}

// DeleteClusterByID 删除 cluster
func (k *K8sCrdClusterProviderImpl) DeleteClusterByID(id uint64) (uint64, error) {
	return k.clusterDbAccess.DeleteByID(id)
}

// FindClusterByID 通过 ID 查找 cluster
func (k *K8sCrdClusterProviderImpl) FindClusterByID(id uint64) (*metaentity.K8sCrdClusterEntity, error) {
	clusterModel, err := k.clusterDbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find cluster with id %d", id)
	}
	if clusterModel == nil {
		return nil, nil
	}
	clusterEntity := &metaentity.K8sCrdClusterEntity{}
	if err = copier.Copy(clusterEntity, clusterModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addonModel, err := k.addonDbAccess.FindByID(clusterEntity.AddonID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with id %d", clusterEntity.AddonID)
	}
	addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
	if err = copier.Copy(addonEntity, addonModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	clusterEntity.AddonInfo = addonEntity

	tagModels, err := k.clusterTagDbAccess.FindByClusterID(clusterEntity.ID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find tags for cluster with id %d", clusterEntity.ID)
	}
	var tagEntities []*metaentity.K8sCrdClusterTagEntity
	if err = copier.Copy(&tagEntities, tagModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	clusterEntity.Tags = tagEntities

	k8sConfigModel, err := k.k8sClusterConfigDbAccess.FindByID(clusterEntity.K8sClusterConfigID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find k8s cluster config with id %d", clusterEntity.K8sClusterConfigID)
	}
	k8sConfigEntity := &metaentity.K8sClusterConfigEntity{}
	if err = copier.Copy(k8sConfigEntity, k8sConfigModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
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
func (k *K8sCrdClusterProviderImpl) FindByParams(params *metaentity.ClusterQueryParams) (
	*metaentity.K8sCrdClusterEntity,
	error,
) {
	clusterModel, err := k.clusterDbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find cluster with params %+v", params)
	}
	if clusterModel == nil {
		return nil, nil
	}

	clusterEntity := metaentity.K8sCrdClusterEntity{}
	if err = copier.Copy(&clusterEntity, clusterModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addonModel, err := k.addonDbAccess.FindByID(clusterModel.AddonID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find addon with id %d", clusterModel.AddonID)
	}

	addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
	if err = copier.Copy(addonEntity, addonModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	clusterEntity.AddonInfo = addonEntity

	return &clusterEntity, nil
}

// UpdateCluster 更新 cluster
func (k *K8sCrdClusterProviderImpl) UpdateCluster(entity *metaentity.K8sCrdClusterEntity) (uint64, error) {
	clusterModel := models.K8sCrdClusterModel{}
	if err := copier.Copy(&clusterModel, entity); err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}

	rows, err := k.clusterDbAccess.Update(&clusterModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update cluster with entity: %+v", entity)
	}
	return rows, nil
}

// ListClusters 查询 cluster 列表
func (k *K8sCrdClusterProviderImpl) ListClusters(
	params *metaentity.ClusterQueryParams,
	pagination *entity.Pagination,
) ([]*metaentity.K8sCrdClusterEntity, uint64, error) {
	clusterModels, count, err := k.clusterDbAccess.ListByPage(params, pagination)
	if err != nil {
		return nil, 0, errors.Wrapf(err, "failed to list cluster with params %+v", params)
	}
	var clusterEntities []*metaentity.K8sCrdClusterEntity
	if err = copier.Copy(&clusterEntities, clusterModels); err != nil {
		return nil, 0, errors.Wrapf(err, "failed to copy")
	}
	for _, clusterEntity := range clusterEntities {
		// 设置 addon 信息
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
		// 设置 k8sClusterConfig 信息
		k8sClusterConfigModel, err := k.k8sClusterConfigDbAccess.FindByID(clusterEntity.K8sClusterConfigID)
		if err != nil {
			slog.Warn("Failed to find clusterModel by ID", "ID", clusterEntity.K8sClusterConfigID, "error", err)
			continue
		}
		k8sClusterConfigEntity := &metaentity.K8sClusterConfigEntity{}
		if err := copier.Copy(k8sClusterConfigEntity, k8sClusterConfigModel); err != nil {
			slog.Warn("Failed to copy model to copied entity", "error", err)
			continue
		}
		clusterEntity.K8sClusterConfig = k8sClusterConfigEntity

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
func (k *K8sCrdClusterProviderImpl) getClusterResource(
	clusterEntity *metaentity.K8sCrdClusterEntity,
) (*coreentity.ClusterResponseData, error) {
	k8sClusterConfigModel, err := k.k8sClusterConfigDbAccess.FindByID(clusterEntity.K8sClusterConfigID)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find k8s cluster config with id %d",
			clusterEntity.K8sClusterConfigID)
	}
	k8sClusterConfigEntity := &metaentity.K8sClusterConfigEntity{}
	if err = copier.Copy(k8sClusterConfigEntity, k8sClusterConfigModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfigEntity)
	if err != nil {
		return nil, errors.Wrap(err, "failed to create k8s client")
	}
	clusterUnStructured, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(clusterEntity.Namespace).
		Get(context.TODO(), clusterEntity.ClusterName, metav1.GetOptions{})
	if err != nil {
		return nil, errors.Wrap(err, "failed to get cluster resource from k8s cluster")
	}
	clusterResource, err := coreentity.GetClusterResponseData(clusterUnStructured)
	if err != nil {
		return nil, errors.Wrap(err, "failed to get cluster resource")
	}
	return clusterResource, nil
}

func (k *K8sCrdClusterProviderImpl) validateProvider() error {
	if k.clusterDbAccess == nil {
		return errors.New("clusterDbAccess is required")
	}
	if k.addonDbAccess == nil {
		return errors.New("addonDbAccess is required")
	}
	if k.k8sClusterConfigDbAccess == nil {
		return errors.New("k8sClusterConfigDbAccess is required")
	}
	if k.addonTopologyDbAccess == nil {
		return errors.New("addonTopologyDbAccess is required")
	}
	if k.clusterTagDbAccess == nil {
		return errors.New("clusterTagDbAccess is required")
	}
	return nil
}

// NewK8sCrdClusterProvider 创建 K8sCrdClusterProvider 接口实现实例
func NewK8sCrdClusterProvider(option ...K8sCrdClusterProviderOptions) (*K8sCrdClusterProviderImpl, error) {
	provider := &K8sCrdClusterProviderImpl{}
	for _, option := range option {
		option(provider)
	}

	if err := provider.validateProvider(); err != nil {
		return nil, errors.Wrap(err, "validate provider failed")
	}
	return provider, nil
}
