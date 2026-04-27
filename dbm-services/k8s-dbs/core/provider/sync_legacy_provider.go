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

	"k8s-dbs/infrastructure/thirdapi"
	infrautil "k8s-dbs/infrastructure/util"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
)

const (
	statusSuccess = "success"
	statusFailed  = "failed"
)

// SyncLegacyResult 存量集群同步到 DBM 的汇总结果
type SyncLegacyResult struct {
	Total   int                `json:"total"`
	Success int                `json:"success"`
	Failed  int                `json:"failed"`
	Details []SyncLegacyDetail `json:"details"`
}

// SyncLegacyDetail 单个集群同步结果
type SyncLegacyDetail struct {
	ClusterID    uint64 `json:"cluster_id"`
	ClusterName  string `json:"cluster_name"`
	Status       string `json:"status"`
	DbmClusterID uint64 `json:"dbm_cluster_id,omitempty"`
	Error        string `json:"error,omitempty"`
}

// SyncFilteredRequest 细粒度同步的过滤参数。
type SyncFilteredRequest struct {
	K8sClusterName string   `json:"k8sClusterName" binding:"required"`
	Namespace      string   `json:"namespace"`
	ClusterNames   []string `json:"clusterNames" binding:"max=50"`
}

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
func (s *SyncLegacyProvider) SyncLegacyClusters() (*SyncLegacyResult, error) {
	clusters, err := s.clusterMetaProvider.ListUnSyncedClusters()
	if err != nil {
		return nil, fmt.Errorf("failed to list unsynced clusters: %w", err)
	}
	return s.syncClusters(clusters, "全量同步"), nil
}

// SyncFilteredClusters 按过滤条件同步指定集群到 DBM
func (s *SyncLegacyProvider) SyncFilteredClusters(req *SyncFilteredRequest) (*SyncLegacyResult, error) {
	var k8sClusterConfigID uint64
	if req.K8sClusterName != "" {
		configEntity, err := s.configProvider.FindConfigByName(req.K8sClusterName)
		if err != nil {
			return nil, fmt.Errorf("查询 K8s 集群配置失败 (k8sClusterName=%s): %w", req.K8sClusterName, err)
		}
		if configEntity == nil {
			return nil, fmt.Errorf("K8s 集群 %q 不存在", req.K8sClusterName)
		}
		k8sClusterConfigID = configEntity.ID
	}

	clusters, err := s.clusterMetaProvider.ListUnSyncedClustersByFilters(
		k8sClusterConfigID, req.Namespace, req.ClusterNames)
	if err != nil {
		return nil, fmt.Errorf("failed to list unsynced clusters by filters: %w", err)
	}
	return s.syncClusters(clusters, "按条件同步"), nil
}

// syncClusters 并发同步一批集群到 DBM（最多 5 个并发）
func (s *SyncLegacyProvider) syncClusters(
	clusters []*metaentity.K8sCrdClusterEntity, label string,
) *SyncLegacyResult {
	result := &SyncLegacyResult{
		Total:   len(clusters),
		Details: make([]SyncLegacyDetail, 0, len(clusters)),
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
func (s *SyncLegacyProvider) syncOneCluster(cluster *metaentity.K8sCrdClusterEntity) SyncLegacyDetail {
	detail := SyncLegacyDetail{
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
