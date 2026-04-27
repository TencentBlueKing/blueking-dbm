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
	"testing"

	"github.com/stretchr/testify/assert"

	"k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
)

// --- mock: K8sClusterConfigProvider ---

type mockConfigProvider struct {
	configs map[string]*metaentity.K8sClusterConfigEntity
	err     error
}

func (m *mockConfigProvider) CreateConfig(_ *metaentity.K8sClusterConfigEntity) (*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}
func (m *mockConfigProvider) DeleteConfigByID(_ uint64) (uint64, error) { return 0, nil }
func (m *mockConfigProvider) FindConfigByID(_ uint64) (*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}
func (m *mockConfigProvider) FindConfigByName(name string) (*metaentity.K8sClusterConfigEntity, error) {
	if m.err != nil {
		return nil, m.err
	}
	if cfg, ok := m.configs[name]; ok {
		return cfg, nil
	}
	return nil, nil
}
func (m *mockConfigProvider) UpdateConfig(_ *metaentity.K8sClusterConfigEntity) (uint64, error) {
	return 0, nil
}
func (m *mockConfigProvider) GetRegionsByVisibility(_ bool) ([]*metaentity.RegionEntity, error) {
	return nil, nil
}
func (m *mockConfigProvider) ListConfigsByLimit(_ int) ([]*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}

// --- mock: K8sCrdClusterProvider ---

type mockClusterProvider struct {
	unsyncedAll      []*metaentity.K8sCrdClusterEntity
	unsyncedFiltered []*metaentity.K8sCrdClusterEntity
	filterArgs       struct {
		configID     uint64
		namespace    string
		clusterNames []string
	}
	err error
}

func (m *mockClusterProvider) CreateCluster(_ *metaentity.K8sCrdClusterEntity) (*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockClusterProvider) DeleteClusterByID(_ uint64) (uint64, error) { return 0, nil }
func (m *mockClusterProvider) FindClusterByID(_ uint64) (*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockClusterProvider) FindByParams(_ *metaentity.ClusterQueryParams) (*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockClusterProvider) UpdateCluster(e *metaentity.K8sCrdClusterEntity) (uint64, error) {
	return 1, nil
}
func (m *mockClusterProvider) ListClusters(_ *metaentity.ClusterQueryParams, _ *entity.Pagination) ([]*metaentity.K8sCrdClusterEntity, uint64, error) {
	return nil, 0, nil
}
func (m *mockClusterProvider) FindClusterTopology(_ uint64) (*metaentity.ClusterTopologyEntity, error) {
	return nil, nil
}
func (m *mockClusterProvider) ListUnSyncedClusters() ([]*metaentity.K8sCrdClusterEntity, error) {
	return m.unsyncedAll, m.err
}
func (m *mockClusterProvider) ListUnSyncedClustersByFilters(
	configID uint64, namespace string, clusterNames []string,
) ([]*metaentity.K8sCrdClusterEntity, error) {
	m.filterArgs.configID = configID
	m.filterArgs.namespace = namespace
	m.filterArgs.clusterNames = clusterNames
	return m.unsyncedFiltered, m.err
}

// --- tests ---

func TestSyncFilteredClusters_K8sClusterNameResolvesToConfigID(t *testing.T) {
	configMock := &mockConfigProvider{
		configs: map[string]*metaentity.K8sClusterConfigEntity{
			"bcs-test": {ID: 42},
		},
	}
	clusterMock := &mockClusterProvider{
		unsyncedFiltered: []*metaentity.K8sCrdClusterEntity{},
	}
	p := NewSyncLegacyProvider(clusterMock, configMock, nil)

	result, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "bcs-test",
	})

	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, uint64(42), clusterMock.filterArgs.configID)
}

func TestSyncFilteredClusters_CombinedFilters(t *testing.T) {
	configMock := &mockConfigProvider{
		configs: map[string]*metaentity.K8sClusterConfigEntity{
			"bcs-prod": {ID: 10},
		},
	}
	clusterMock := &mockClusterProvider{
		unsyncedFiltered: []*metaentity.K8sCrdClusterEntity{},
	}
	p := NewSyncLegacyProvider(clusterMock, configMock, nil)

	_, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "bcs-prod",
		Namespace:      "dbs-ns",
		ClusterNames:   []string{"cluster-a"},
	})

	assert.NoError(t, err)
	assert.Equal(t, uint64(10), clusterMock.filterArgs.configID)
	assert.Equal(t, "dbs-ns", clusterMock.filterArgs.namespace)
	assert.Equal(t, []string{"cluster-a"}, clusterMock.filterArgs.clusterNames)
}

func TestSyncFilteredClusters_K8sClusterWithNamespace(t *testing.T) {
	configMock := &mockConfigProvider{
		configs: map[string]*metaentity.K8sClusterConfigEntity{
			"bcs-prod": {ID: 20},
		},
	}
	clusterMock := &mockClusterProvider{
		unsyncedFiltered: []*metaentity.K8sCrdClusterEntity{},
	}
	p := NewSyncLegacyProvider(clusterMock, configMock, nil)

	result, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "bcs-prod",
		Namespace:      "production",
	})

	assert.NoError(t, err)
	assert.Equal(t, 0, result.Total)
	assert.Equal(t, uint64(20), clusterMock.filterArgs.configID)
	assert.Equal(t, "production", clusterMock.filterArgs.namespace)
	assert.Nil(t, clusterMock.filterArgs.clusterNames)
}

func TestSyncLegacyClusters_Empty(t *testing.T) {
	clusterMock := &mockClusterProvider{
		unsyncedAll: []*metaentity.K8sCrdClusterEntity{},
	}
	p := NewSyncLegacyProvider(clusterMock, &mockConfigProvider{}, nil)

	result, err := p.SyncLegacyClusters()

	assert.NoError(t, err)
	assert.Equal(t, 0, result.Total)
	assert.Equal(t, 0, result.Success)
	assert.Equal(t, 0, result.Failed)
	assert.Empty(t, result.Details)
}

func TestSyncLegacyClusters_ListError(t *testing.T) {
	clusterMock := &mockClusterProvider{
		err: fmt.Errorf("database unavailable"),
	}
	p := NewSyncLegacyProvider(clusterMock, &mockConfigProvider{}, nil)

	_, err := p.SyncLegacyClusters()

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "database unavailable")
}

func TestSyncFilteredClusters_K8sClusterNameNotFound(t *testing.T) {
	configMock := &mockConfigProvider{
		configs: map[string]*metaentity.K8sClusterConfigEntity{},
	}
	p := NewSyncLegacyProvider(&mockClusterProvider{}, configMock, nil)

	_, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "nonexistent",
	})

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "不存在")
}

func TestSyncFilteredClusters_ConfigProviderError(t *testing.T) {
	configMock := &mockConfigProvider{
		err: fmt.Errorf("db connection refused"),
	}
	p := NewSyncLegacyProvider(&mockClusterProvider{}, configMock, nil)

	_, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "some-cluster",
	})

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "db connection refused")
}

func TestSyncFilteredClusters_ClusterProviderError(t *testing.T) {
	configMock := &mockConfigProvider{
		configs: map[string]*metaentity.K8sClusterConfigEntity{
			"bcs-test": {ID: 1},
		},
	}
	clusterMock := &mockClusterProvider{
		err: fmt.Errorf("query timeout"),
	}
	p := NewSyncLegacyProvider(clusterMock, configMock, nil)

	_, err := p.SyncFilteredClusters(&SyncFilteredRequest{
		K8sClusterName: "bcs-test",
		Namespace:      "test-ns",
	})

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "query timeout")
}
