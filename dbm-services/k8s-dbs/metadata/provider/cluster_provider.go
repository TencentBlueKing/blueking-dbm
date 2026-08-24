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
	"sync"

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
	ListUnSyncedClusters() ([]*metaentity.K8sCrdClusterEntity, error)
	ListUnSyncedClustersByFilters(k8sClusterConfigID uint64, namespace string, clusterNames []string) (
		[]*metaentity.K8sCrdClusterEntity, error)
}

// UpdateClusterMetadataRequest 外部系统更新集群元数据请求
// 定位字段必填，更新字段为可选（nil 表示不更新）
type UpdateClusterMetadataRequest struct {
	Namespace   string `json:"namespace" binding:"required"`
	ClusterName string `json:"clusterName" binding:"required"`

	DbmClusterID        *uint64   `json:"dbmClusterId"`
	BkBizID             *uint64   `json:"bkBizId"`
	BkBizName           *string   `json:"bkBizName"`
	BkAppAbbr           *string   `json:"bkAppAbbr"`
	BkAppCode           *string   `json:"bkAppCode"`
	ClusterAlias        *string   `json:"clusterAlias"`
	VIP                 *string   `json:"vip"`
	Description         *string   `json:"description"`
	TopoName            *string   `json:"topoName"`
	ServiceVersion      *string   `json:"serviceVersion"`
	AddonClusterVersion *string   `json:"addonClusterVersion"`
	Tags                *[]string `json:"tags"`
	UpdatedBy           string    `json:"updatedBy"`
}

// ApplyTo 将请求中的非空更新字段应用到集群实体
func (r *UpdateClusterMetadataRequest) ApplyTo(entity *metaentity.K8sCrdClusterEntity) {
	if r.DbmClusterID != nil {
		entity.DbmClusterID = *r.DbmClusterID
	}
	if r.BkBizID != nil {
		entity.BkBizID = *r.BkBizID
	}
	if r.BkBizName != nil {
		entity.BkBizName = *r.BkBizName
	}
	if r.BkAppAbbr != nil {
		entity.BkAppAbbr = *r.BkAppAbbr
	}
	if r.BkAppCode != nil {
		entity.BkAppCode = *r.BkAppCode
	}
	if r.ClusterAlias != nil {
		entity.ClusterAlias = *r.ClusterAlias
	}
	if r.VIP != nil {
		entity.VIP = *r.VIP
	}
	if r.Description != nil {
		entity.Description = *r.Description
	}
	if r.TopoName != nil {
		entity.TopoName = *r.TopoName
	}
	if r.ServiceVersion != nil {
		entity.ServiceVersion = *r.ServiceVersion
	}
	if r.AddonClusterVersion != nil {
		entity.AddonClusterVersion = *r.AddonClusterVersion
	}
	if r.Tags != nil {
		tagEntities := make([]*metaentity.K8sCrdClusterTagEntity, 0, len(*r.Tags))
		for _, tag := range *r.Tags {
			tagEntities = append(tagEntities, &metaentity.K8sCrdClusterTagEntity{
				ClusterTag: tag,
				Active:     true,
			})
		}
		entity.Tags = tagEntities
	}
	if r.UpdatedBy != "" {
		entity.UpdatedBy = r.UpdatedBy
	}
}

// K8sCrdClusterProviderImpl K8sCrlClusterProvider 具体实现
type K8sCrdClusterProviderImpl struct {
	clusterDbAccess          dbaccess.K8sCrdClusterDbAccess
	addonDbAccess            dbaccess.K8sCrdStorageAddonDbAccess
	clusterTagDbAccess       dbaccess.K8sCrdClusterTagDbAccess
	k8sClusterConfigDbAccess dbaccess.K8sClusterConfigDbAccess
	addonTopologyDbAccess    dbaccess.AddonTopologyDbAccess
	addonTypeDbAccess        dbaccess.AddonTypeDbAccess
}

var (
	clusterInstance K8sCrdClusterProvider
	clusterOnce     sync.Once
)

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

// WithAddonTypeDbAccess 设置 WithAddonTypeDbAccess
func (k *K8sCrdClusterProviderBuilder) WithAddonTypeDbAccess(
	access dbaccess.AddonTypeDbAccess,
) K8sCrdClusterProviderOptions {
	return func(k *K8sCrdClusterProviderImpl) {
		k.addonTypeDbAccess = access
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

	if entity.Tags != nil {
		if _, err := k.clusterTagDbAccess.DeleteByClusterID(clusterModel.ID); err != nil {
			return rows, errors.Wrapf(err, "failed to delete old tags for cluster %d", clusterModel.ID)
		}
		if len(entity.Tags) > 0 {
			tagModels := make([]*models.K8sCrdClusterTagModel, 0, len(entity.Tags))
			for _, tag := range entity.Tags {
				tagModels = append(tagModels, &models.K8sCrdClusterTagModel{
					CrdClusterID: clusterModel.ID,
					ClusterTag:   tag.ClusterTag,
					Active:       true,
					CreatedBy:    entity.UpdatedBy,
					UpdatedBy:    entity.UpdatedBy,
				})
			}
			if _, err := k.clusterTagDbAccess.BatchCreate(tagModels); err != nil {
				return rows, errors.Wrapf(err, "failed to batch create tags for cluster %d", clusterModel.ID)
			}
		}
	}
	return rows, nil
}

// ListClusters 查询 cluster 列表
func (k *K8sCrdClusterProviderImpl) ListClusters(
	params *metaentity.ClusterQueryParams,
	pagination *entity.Pagination,
) ([]*metaentity.K8sCrdClusterEntity, uint64, error) {
	clusterModels, count, err := k.clusterDbAccess.ListActiveByPage(params, pagination)
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

// buildClusterEntitiesWithAddon 将 cluster model 列表转换为带 AddonInfo 的 entity 列表。
// 转换失败或 addon 查询失败的条目会被跳过并记录警告日志。
func (k *K8sCrdClusterProviderImpl) buildClusterEntitiesWithAddon(
	clusterModels []*models.K8sCrdClusterModel,
) []*metaentity.K8sCrdClusterEntity {
	var clusterEntities []*metaentity.K8sCrdClusterEntity
	for _, clusterModel := range clusterModels {
		clusterEntity := &metaentity.K8sCrdClusterEntity{}
		if err := copier.Copy(clusterEntity, clusterModel); err != nil {
			slog.Warn("Failed to copy cluster model to entity", "cluster_id", clusterModel.ID, "error", err)
			continue
		}

		// 加载 AddonInfo（同步到 DBM 需要 AddonType 来映射 cluster type）
		addonModel, err := k.addonDbAccess.FindByID(clusterModel.AddonID)
		if err != nil {
			slog.Warn("Failed to find addon for cluster",
				"cluster_id", clusterModel.ID,
				"addon_id", clusterModel.AddonID,
				"error", err)
			continue
		}
		addonEntity := &metaentity.K8sCrdStorageAddonEntity{}
		if err := copier.Copy(addonEntity, addonModel); err != nil {
			slog.Warn("Failed to copy addon model to entity", "addon_id", clusterModel.AddonID, "error", err)
			continue
		}
		clusterEntity.AddonInfo = addonEntity
		clusterEntities = append(clusterEntities, clusterEntity)
	}
	return clusterEntities
}

// ListUnSyncedClusters 查询所有 dbm_cluster_id 为 0 或 NULL 的存量集群，并加载 AddonInfo
func (k *K8sCrdClusterProviderImpl) ListUnSyncedClusters() ([]*metaentity.K8sCrdClusterEntity, error) {
	clusterModels, err := k.clusterDbAccess.ListByDbmClusterIDZero()
	if err != nil {
		return nil, errors.Wrap(err, "failed to list unsynced clusters")
	}
	return k.buildClusterEntitiesWithAddon(clusterModels), nil
}

// ListUnSyncedClustersByFilters 按过滤条件查询未同步集群，并加载 AddonInfo
func (k *K8sCrdClusterProviderImpl) ListUnSyncedClustersByFilters(
	k8sClusterConfigID uint64, namespace string, clusterNames []string,
) ([]*metaentity.K8sCrdClusterEntity, error) {
	clusterModels, err := k.clusterDbAccess.ListUnSyncedByFilters(k8sClusterConfigID, namespace, clusterNames)
	if err != nil {
		return nil, errors.Wrap(err, "failed to list unsynced clusters by filters")
	}
	return k.buildClusterEntitiesWithAddon(clusterModels), nil
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
	if k.addonTypeDbAccess == nil {
		return errors.New("addonTypeDbAccess is required")
	}
	return nil
}

// GetK8sCrdClusterProvider 获取 K8sCrdClusterProvider 单例实例
func GetK8sCrdClusterProvider(options ...K8sCrdClusterProviderOptions) K8sCrdClusterProvider {
	clusterOnce.Do(func() {
		provider := &K8sCrdClusterProviderImpl{}
		for _, option := range options {
			option(provider)
		}

		if err := provider.validateProvider(); err != nil {
			panic(errors.Wrap(err, "validate provider failed"))
		}
		clusterInstance = provider
	})
	if clusterInstance == nil {
		panic("K8sCrdClusterProvider instance is nil after initialization")
	}
	return clusterInstance
}
