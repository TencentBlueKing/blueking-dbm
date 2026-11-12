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
	"fmt"
	"log/slog"
	"sync"

	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/infrastructure/thirdapi"
	infrautil "k8s-dbs/infrastructure/util"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
)

const (
	statusSuccess = "success"
	statusFailed  = "failed"
	statusSkipped = "skipped"
)

// SyncLegacyProvider 存量集群同步 Provider
type SyncLegacyProvider struct {
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
	configProvider      metaprovider.K8sClusterConfigProvider
	dbmAPIService       *thirdapi.DbmAPIService
}

// NewSyncLegacyProvider 创建 SyncLegacyProvider 实例
func NewSyncLegacyProvider(
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	configProvider metaprovider.K8sClusterConfigProvider,
	dbmAPIService *thirdapi.DbmAPIService,
) *SyncLegacyProvider {
	return &SyncLegacyProvider{
		clusterMetaProvider: clusterMetaProvider,
		configProvider:      configProvider,
		dbmAPIService:       dbmAPIService,
	}
}

// SyncLegacyClusters 将所有 dbm_cluster_id = 0 的存量集群同步到 DBM 并回写 ID
func (s *SyncLegacyProvider) SyncLegacyClusters() (*coreentity.SyncLegacyResult, error) {
	clusters, err := s.clusterMetaProvider.ListUnSyncedClusters()
	if err != nil {
		return nil, fmt.Errorf("failed to list unsynced clusters: %w", err)
	}
	return s.syncClusters(clusters, "全量同步"), nil
}

// SyncFilteredClusters 按过滤条件同步指定集群到 DBM
func (s *SyncLegacyProvider) SyncFilteredClusters(params *coreentity.SyncFilteredParams) (
	*coreentity.SyncLegacyResult, error,
) {
	var k8sClusterConfigID uint64
	if params.K8sClusterName != "" {
		configEntity, err := s.configProvider.FindConfigByName(params.K8sClusterName)
		if err != nil {
			return nil, fmt.Errorf("查询 K8s 集群配置失败 (k8sClusterName=%s): %w", params.K8sClusterName, err)
		}
		if configEntity == nil {
			return nil, fmt.Errorf("K8s 集群 %q 不存在", params.K8sClusterName)
		}
		k8sClusterConfigID = configEntity.ID
	}

	clusters, err := s.clusterMetaProvider.ListUnSyncedClustersByFilters(
		k8sClusterConfigID, params.Namespace, params.ClusterNames)
	if err != nil {
		return nil, fmt.Errorf("failed to list unsynced clusters by filters: %w", err)
	}
	return s.syncClusters(clusters, "按条件同步"), nil
}

// syncClusters 并发同步一批集群到 DBM（最多 5 个并发）
func (s *SyncLegacyProvider) syncClusters(
	clusters []*metaentity.K8sCrdClusterEntity, label string,
) *coreentity.SyncLegacyResult {
	result := &coreentity.SyncLegacyResult{
		Total:   len(clusters),
		Details: make([]coreentity.SyncLegacyDetail, 0, len(clusters)),
	}
	if len(clusters) == 0 {
		return result
	}

	const maxConcurrency = 5
	sem := make(chan struct{}, maxConcurrency)

	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, cluster := range clusters {
		wg.Add(1)
		sem <- struct{}{}

		go func(c *metaentity.K8sCrdClusterEntity) {
			defer wg.Done()
			defer func() { <-sem }()

			detail := s.syncOneCluster(c)

			mu.Lock()
			result.Details = append(result.Details, detail)
			if detail.Status == statusSuccess {
				result.Success++
			} else {
				result.Failed++
			}
			mu.Unlock()
		}(cluster)
	}

	wg.Wait()

	slog.Info(label+"完成",
		"total", result.Total,
		"success", result.Success,
		"failed", result.Failed,
	)
	return result
}

// syncOneCluster 同步单个集群到 DBM 并回写 ID
func (s *SyncLegacyProvider) syncOneCluster(cluster *metaentity.K8sCrdClusterEntity) coreentity.SyncLegacyDetail {
	detail := coreentity.SyncLegacyDetail{
		ClusterID:   cluster.ID,
		ClusterName: cluster.ClusterName,
	}

	// 获取 DBM cluster type
	if cluster.AddonInfo == nil {
		detail.Status = statusFailed
		detail.Error = "addon info is nil"
		return detail
	}

	dbmClusterType, err := infrautil.GetDbmClusterType(cluster.AddonInfo.AddonType, cluster.TopoName)
	if err != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("failed to get dbm cluster type: %v", err)
		return detail
	}

	// 构建创建请求并调用 DBM API
	syncRequest := infrautil.BuildCreateRequest(cluster, dbmClusterType)
	dbmClusterID, err := s.dbmAPIService.SyncClusterCreated(syncRequest)
	if err != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("failed to sync to DBM: %v", err)
		return detail
	}

	// 回写 dbm_cluster_id
	cluster.DbmClusterID = dbmClusterID
	if _, err := s.clusterMetaProvider.UpdateCluster(cluster); err != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("synced to DBM (id=%d) but failed to write back: %v", dbmClusterID, err)
		return detail
	}

	detail.Status = statusSuccess
	detail.DbmClusterID = dbmClusterID

	slog.Info("存量集群同步成功",
		"cluster_id", cluster.ID,
		"cluster_name", cluster.ClusterName,
		"dbm_cluster_id", dbmClusterID,
	)

	return detail
}

// SyncOneCluster 精确同步单个集群：按 k8sClusterName+namespace+clusterName 定位集群，
// 幂等同步 cluster 元数据到 DBM，并使用手动传入的 domain 与 instances 创建 DBM 域名记录。
func (s *SyncLegacyProvider) SyncOneCluster(params *coreentity.SyncOneParams) (*coreentity.SyncLegacyDetail, error) {
	configEntity, err := s.configProvider.FindConfigByName(params.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("查询 K8s 集群配置失败 (k8sClusterName=%s): %w", params.K8sClusterName, err)
	}
	if configEntity == nil {
		return nil, fmt.Errorf("K8s 集群 %q 不存在", params.K8sClusterName)
	}

	cluster, err := s.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		ClusterName:        params.ClusterName,
		Namespace:          params.Namespace,
		K8sClusterConfigID: configEntity.ID,
	})
	if err != nil {
		return nil, fmt.Errorf("查询集群元数据失败 (clusterName=%s, namespace=%s): %w",
			params.ClusterName, params.Namespace, err)
	}
	if cluster == nil {
		return nil, fmt.Errorf("集群 %q (namespace=%s) 不存在", params.ClusterName, params.Namespace)
	}

	// DbmClusterID != 0 表示该集群已同步过，整体跳过 cluster 与 domain，避免重复操作。
	if cluster.DbmClusterID != 0 {
		slog.Info("精确同步: 集群已同步，整体跳过",
			"cluster_id", cluster.ID,
			"cluster_name", cluster.ClusterName,
			"dbm_cluster_id", cluster.DbmClusterID,
		)
		return &coreentity.SyncLegacyDetail{
			ClusterID:    cluster.ID,
			ClusterName:  cluster.ClusterName,
			Status:       statusSkipped,
			DbmClusterID: cluster.DbmClusterID,
			Error:        fmt.Sprintf("集群已同步 (dbm_cluster_id=%d)，跳过", cluster.DbmClusterID),
		}, nil
	}

	detail := s.syncOneClusterWithDomain(cluster, params)
	return &detail, nil
}

// syncOneClusterWithDomain 同步 cluster 元数据后，使用手动 domain+instances 同步域名记录。
// 严格保证"先 cluster 后 domain"：domain 创建依赖 DBM 侧已存在的 cluster。
func (s *SyncLegacyProvider) syncOneClusterWithDomain(
	cluster *metaentity.K8sCrdClusterEntity, params *coreentity.SyncOneParams,
) coreentity.SyncLegacyDetail {
	detail := coreentity.SyncLegacyDetail{
		ClusterID:   cluster.ID,
		ClusterName: cluster.ClusterName,
	}

	if cluster.AddonInfo == nil {
		detail.Status = statusFailed
		detail.Error = "addon info is nil"
		return detail
	}

	dbmClusterType, err := infrautil.GetDbmClusterType(cluster.AddonInfo.AddonType, cluster.TopoName)
	if err != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("failed to get dbm cluster type: %v", err)
		return detail
	}

	// 1) 同步 cluster 元数据并回写 dbm_cluster_id。
	// 调用方已保证仅在 DbmClusterID == 0（未同步）时进入本方法。
	syncRequest := infrautil.BuildManualCreateRequest(cluster, dbmClusterType, params.ImmuteDomain, params.Region)
	dbmClusterID, createErr := s.dbmAPIService.SyncClusterCreated(syncRequest)
	if createErr != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("failed to sync cluster to DBM: %v", createErr)
		return detail
	}
	cluster.DbmClusterID = dbmClusterID
	if _, upErr := s.clusterMetaProvider.UpdateCluster(cluster); upErr != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("synced cluster to DBM (id=%d) but failed to write back: %v",
			dbmClusterID, upErr)
		return detail
	}
	slog.Info("精确同步: cluster 同步成功",
		"cluster_id", cluster.ID,
		"cluster_name", cluster.ClusterName,
		"dbm_cluster_id", dbmClusterID,
	)
	detail.DbmClusterID = cluster.DbmClusterID

	// 2) 同步 domain（此时 DBM 侧 cluster 已存在）。
	if domainErr := infrautil.SyncDomainCreateBlocking(
		cluster, s.dbmAPIService, dbmClusterType, params.Domain, params.Instances,
	); domainErr != nil {
		detail.Status = statusFailed
		detail.Error = fmt.Sprintf("cluster 已同步成功 (dbm_cluster_id=%d)，domain 同步失败: %v",
			cluster.DbmClusterID, domainErr)
		return detail
	}

	detail.Status = statusSuccess
	slog.Info("精确同步: domain 同步成功",
		"cluster_id", cluster.ID,
		"cluster_name", cluster.ClusterName,
		"dbm_cluster_id", cluster.DbmClusterID,
		"domain", params.Domain,
	)
	return detail
}
