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

package middleware

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"k8s-dbs/common/constant"
	"k8s-dbs/common/entity"
	metaentity "k8s-dbs/metadata/entity"
)

// --- mock providers ---

type mockK8sClusterConfigProvider struct {
	config *metaentity.K8sClusterConfigEntity
	err    error
}

func (m *mockK8sClusterConfigProvider) CreateConfig(_ *metaentity.K8sClusterConfigEntity) (*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}
func (m *mockK8sClusterConfigProvider) DeleteConfigByID(_ uint64) (uint64, error) { return 0, nil }
func (m *mockK8sClusterConfigProvider) FindConfigByID(_ uint64) (*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}
func (m *mockK8sClusterConfigProvider) FindConfigByName(_ string) (*metaentity.K8sClusterConfigEntity, error) {
	return m.config, m.err
}
func (m *mockK8sClusterConfigProvider) UpdateConfig(_ *metaentity.K8sClusterConfigEntity) (uint64, error) {
	return 0, nil
}
func (m *mockK8sClusterConfigProvider) GetRegionsByVisibility(_ bool) ([]*metaentity.RegionEntity, error) {
	return nil, nil
}
func (m *mockK8sClusterConfigProvider) ListConfigsByLimit(_ int) ([]*metaentity.K8sClusterConfigEntity, error) {
	return nil, nil
}

type mockK8sCrdClusterProvider struct {
	cluster *metaentity.K8sCrdClusterEntity
	err     error
}

func (m *mockK8sCrdClusterProvider) CreateCluster(_ *metaentity.K8sCrdClusterEntity) (*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockK8sCrdClusterProvider) DeleteClusterByID(_ uint64) (uint64, error) { return 0, nil }
func (m *mockK8sCrdClusterProvider) FindClusterByID(_ uint64) (*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockK8sCrdClusterProvider) FindByParams(_ *metaentity.ClusterQueryParams) (*metaentity.K8sCrdClusterEntity, error) {
	return m.cluster, m.err
}
func (m *mockK8sCrdClusterProvider) UpdateCluster(_ *metaentity.K8sCrdClusterEntity) (uint64, error) {
	return 0, nil
}
func (m *mockK8sCrdClusterProvider) ListClusters(_ *metaentity.ClusterQueryParams, _ *entity.Pagination) ([]*metaentity.K8sCrdClusterEntity, uint64, error) {
	return nil, 0, nil
}
func (m *mockK8sCrdClusterProvider) FindClusterTopology(_ uint64) (*metaentity.ClusterTopologyEntity, error) {
	return nil, nil
}
func (m *mockK8sCrdClusterProvider) ListUnSyncedClusters() ([]*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}
func (m *mockK8sCrdClusterProvider) ListUnSyncedClustersByFilters(_ uint64, _ string, _ []string) ([]*metaentity.K8sCrdClusterEntity, error) {
	return nil, nil
}

// newTestResolver 构建已初始化的测试 resolver
func newTestResolver(
	configProvider *mockK8sClusterConfigProvider,
	clusterProvider *mockK8sCrdClusterProvider,
) *DBClusterTypeResolver {
	r := &DBClusterTypeResolver{
		configProvider:  configProvider,
		clusterProvider: clusterProvider,
	}
	// 标记已初始化，跳过 initProviders 的 sync.Once
	r.once.Do(func() {})
	return r
}

// --- 创建操作测试 ---

func TestResolve_Create_TopLevelStorageAddonType(t *testing.T) {
	r := newTestResolver(nil, nil)

	result, err := r.Resolve(constant.APIClusterCreate, []byte(`{"storageAddonType":"surrealdb","topoName":"surreal-tikv"}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_surrealdb_ha", result.ClusterType)
	assert.Equal(t, "surrealdb", result.AddonType)
	assert.Equal(t, uint64(0), result.DbmClusterID, "create operation should have DbmClusterID=0")
}

func TestResolve_Create_NestedStorageAddonType(t *testing.T) {
	r := newTestResolver(nil, nil)

	result, err := r.Resolve(constant.APIClusterCreate, []byte(`{"basicInfo":{"storageAddonType":"victoriametrics"}}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_victoriametrics_ha", result.ClusterType)
	assert.Equal(t, "victoriametrics", result.AddonType)
}

func TestResolve_Create_MissingStorageAddonType(t *testing.T) {
	r := newTestResolver(nil, nil)

	_, err := r.Resolve(constant.APIClusterCreate, []byte(`{"clusterName":"test-cluster"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "storageAddonType")
}

func TestResolve_Create_UnknownStorageAddonType(t *testing.T) {
	r := newTestResolver(nil, nil)

	_, err := r.Resolve(constant.APIClusterCreate, []byte(`{"storageAddonType":"unknowndb"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "未知的 addon 类型")
}

// --- 非创建操作测试 ---

func TestResolve_NonCreate_DBQuerySuccess(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 42, ClusterName: "bcs-test"},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo:    &metaentity.K8sCrdStorageAddonEntity{AddonType: "qdrant"},
			TopoName:     "cluster",
			DbmClusterID: 999,
		},
	}
	r := newTestResolver(configMock, clusterMock)

	result, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns-1","clusterName":"my-qdrant"}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_qdrant_ha", result.ClusterType)
	assert.Equal(t, "qdrant", result.AddonType)
	assert.Equal(t, uint64(999), result.DbmClusterID)
}

func TestResolve_NonCreate_DbmClusterIDZero(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 42, ClusterName: "bcs-test"},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo:    &metaentity.K8sCrdStorageAddonEntity{AddonType: "qdrant"},
			TopoName:     "cluster",
			DbmClusterID: 0, // 尚未同步到 DBM
		},
	}
	r := newTestResolver(configMock, clusterMock)

	result, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns-1","clusterName":"my-qdrant"}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_qdrant_ha", result.ClusterType)
	assert.Equal(t, uint64(0), result.DbmClusterID)
}

func TestResolve_NonCreate_MissingFields(t *testing.T) {
	r := newTestResolver(&mockK8sClusterConfigProvider{}, &mockK8sCrdClusterProvider{})

	tests := []struct {
		name    string
		rawJSON []byte
	}{
		{"missing k8sClusterName", []byte(`{"namespace":"ns","clusterName":"c"}`)},
		{"missing namespace", []byte(`{"k8sClusterName":"k","clusterName":"c"}`)},
		{"missing clusterName", []byte(`{"k8sClusterName":"k","namespace":"ns"}`)},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := r.Resolve(constant.APIClusterDelete, tc.rawJSON)
			require.Error(t, err)
			assert.True(t, IsResolverError(err))
			assert.Contains(t, err.Error(), "缺少必要字段")
		})
	}
}

func TestResolve_NonCreate_ConfigNotFound(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{config: nil, err: nil}
	r := newTestResolver(configMock, &mockK8sCrdClusterProvider{})

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"nonexistent","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "不存在")
}

func TestResolve_NonCreate_ConfigQueryError(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{err: fmt.Errorf("db connection lost")}
	r := newTestResolver(configMock, &mockK8sCrdClusterProvider{})

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "查询 K8s 集群配置失败")
}

func TestResolve_NonCreate_ClusterNotFound(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{cluster: nil, err: nil}
	r := newTestResolver(configMock, clusterMock)

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"nonexistent"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "集群不存在")
}

func TestResolve_NonCreate_ClusterQueryError(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{err: fmt.Errorf("query timeout")}
	r := newTestResolver(configMock, clusterMock)

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "查询集群失败")
}

func TestResolve_NonCreate_UnknownAddonType(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo: &metaentity.K8sCrdStorageAddonEntity{AddonType: "unknowndb"},
		},
	}
	r := newTestResolver(configMock, clusterMock)

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "未知的 addon 类型")
}

// --- 安全性测试 ---

func TestResolve_NonCreate_ExplicitClusterType_Consistent(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo:    &metaentity.K8sCrdStorageAddonEntity{AddonType: "surrealdb"},
			TopoName:     "surreal-tikv",
			DbmClusterID: 123,
		},
	}
	r := newTestResolver(configMock, clusterMock)

	result, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c","cluster_type":"k8s_surrealdb_ha"}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_surrealdb_ha", result.ClusterType)
	assert.Equal(t, uint64(123), result.DbmClusterID)
}

func TestResolve_NonCreate_ExplicitClusterType_Inconsistent(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo: &metaentity.K8sCrdStorageAddonEntity{AddonType: "surrealdb"},
			TopoName:  "surreal-tikv",
		},
	}
	r := newTestResolver(configMock, clusterMock)

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c","cluster_type":"k8s_qdrant_ha"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "不一致")
}

// --- 懒加载测试 ---

func TestResolve_NonCreate_ProviderNotInitialized(t *testing.T) {
	// 模拟 provider 未初始化：once 已执行但设置了 initErr
	r := &DBClusterTypeResolver{
		initErr: fmt.Errorf("provider 尚未初始化: K8sCrdClusterProvider instance is nil"),
	}
	r.once.Do(func() {}) // 标记 once 已执行

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "初始化失败")
}

// --- 嵌套字段提取测试 ---

func TestResolve_NonCreate_NestedFields(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 5},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo:    &metaentity.K8sCrdStorageAddonEntity{AddonType: "risingwave"},
			TopoName:     "risingwave",
			DbmClusterID: 77,
		},
	}
	r := newTestResolver(configMock, clusterMock)

	// 模拟 Dataweb API 嵌套结构
	result, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"deploymentEnv":{"k8sClusterName":"bcs-dataweb"},"basicInfo":{"namespace":"rw-ns","clusterName":"rw-cluster"}}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_risingwave_ha", result.ClusterType)
	assert.Equal(t, "risingwave", result.AddonType)
	assert.Equal(t, uint64(77), result.DbmClusterID)
}

// --- gjsonFirstString 辅助测试 ---

func TestGjsonFirstString_TopLevelPriority(t *testing.T) {
	raw := []byte(`{"key":"topValue","nested":{"key":"nestedValue"}}`)

	val := gjsonFirstString(raw, "key", "nested.key")
	assert.Equal(t, "topValue", val)
}

func TestGjsonFirstString_FallbackToNested(t *testing.T) {
	raw := []byte(`{"nested":{"key":"nestedValue"}}`)

	val := gjsonFirstString(raw, "key", "nested.key")
	assert.Equal(t, "nestedValue", val)
}

func TestGjsonFirstString_NotFound(t *testing.T) {
	raw := []byte(`{"other":"value"}`)

	val := gjsonFirstString(raw, "key", "nested.key")
	assert.Equal(t, "", val)
}

func TestResolve_NonCreate_NilAddonInfo(t *testing.T) {
	configMock := &mockK8sClusterConfigProvider{
		config: &metaentity.K8sClusterConfigEntity{ID: 1},
	}
	clusterMock := &mockK8sCrdClusterProvider{
		cluster: &metaentity.K8sCrdClusterEntity{
			AddonInfo: nil,
		},
	}
	r := newTestResolver(configMock, clusterMock)

	_, err := r.Resolve(constant.APIClusterDelete,
		[]byte(`{"k8sClusterName":"bcs-test","namespace":"ns","clusterName":"c"}`))

	require.Error(t, err)
	assert.True(t, IsResolverError(err))
	assert.Contains(t, err.Error(), "AddonInfo 为空")
}

// --- Create 场景的安全性：显式 cluster_type 被信任 ---

func TestResolve_Create_ExplicitClusterType_Trusted(t *testing.T) {
	r := newTestResolver(nil, nil)

	result, err := r.Resolve(constant.APIClusterCreate,
		[]byte(`{"storageAddonType":"milvus","cluster_type":"k8s_milvus_ha"}`))

	require.NoError(t, err)
	assert.Equal(t, "k8s_milvus_ha", result.ClusterType)
	assert.Equal(t, "milvus", result.AddonType)
}

// --- Addon 操作测试 ---
// addon 操作（install/uninstall/upgrade）不在 APIToIAMAction 映射中，
// 中间件直接放行，不会调用 Resolve。此处不再测试 addon 的 resolve 逻辑。
