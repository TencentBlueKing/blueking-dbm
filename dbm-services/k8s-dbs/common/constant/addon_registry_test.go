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

package constant

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestAddonIAMRegistry_NoDuplicateClusterType(t *testing.T) {
	seen := make(map[string]bool)
	for _, entry := range addonIAMRegistry {
		assert.False(t, seen[entry.DbmClusterType],
			"duplicate ClusterType in registry: %s", entry.DbmClusterType)
		seen[entry.DbmClusterType] = true
	}
}

func TestAddonIAMRegistry_EntryCount(t *testing.T) {
	assert.Equal(t, 7, len(addonIAMRegistry),
		"registry should have exactly 7 entries (surrealdb ha+single, 5 others ha)")
}

func TestAddonIAMRegistry_AllAddonsPresent(t *testing.T) {
	expectedAddons := map[string]bool{
		"surrealdb": false, "victoriametrics": false, "risingwave": false,
		"greptimedb": false, "milvus": false, "qdrant": false,
	}
	for _, entry := range addonIAMRegistry {
		expectedAddons[entry.AddonType] = true
	}
	for addon, found := range expectedAddons {
		assert.True(t, found, "addon %s should be in registry", addon)
	}
}

func TestClusterTypeToIAMPrefix_MapsToCorrectPrefix(t *testing.T) {
	expected := map[string]string{
		"k8s_surrealdb_ha":       "k8s_surrealdb",
		"k8s_surrealdb_single":   "k8s_surrealdb",
		"k8s_victoriametrics_ha": "k8s_victoriametrics",
		"k8s_risingwave_ha":      "k8s_risingwave",
		"k8s_greptimedb_ha":      "k8s_greptimedb",
		"k8s_milvus_ha":          "k8s_milvus",
		"k8s_qdrant_ha":          "k8s_qdrant",
	}
	for ct, expectedPrefix := range expected {
		prefix, exists := ClusterTypeToIAMPrefix[ct]
		assert.True(t, exists, "cluster type %s should be in ClusterTypeToIAMPrefix", ct)
		assert.Equal(t, expectedPrefix, prefix)
	}
}

func TestResolveClusterType_SurrealdbHA(t *testing.T) {
	ct, ok := ResolveClusterType("surrealdb", "surreal-tikv")
	assert.True(t, ok)
	assert.Equal(t, "k8s_surrealdb_ha", ct)
}

func TestResolveClusterType_SurrealdbSingle(t *testing.T) {
	for _, topo := range []string{"surreal-rocksdb", "surreal-memory"} {
		ct, ok := ResolveClusterType("surrealdb", topo)
		assert.True(t, ok, "topo %s should resolve", topo)
		assert.Equal(t, "k8s_surrealdb_single", ct, "topo %s should resolve to single", topo)
	}
}

func TestResolveClusterType_CatchAll(t *testing.T) {
	catchAllAddons := []struct {
		addonType  string
		expectedCT string
	}{
		{"victoriametrics", "k8s_victoriametrics_ha"},
		{"risingwave", "k8s_risingwave_ha"},
		{"greptimedb", "k8s_greptimedb_ha"},
		{"milvus", "k8s_milvus_ha"},
		{"qdrant", "k8s_qdrant_ha"},
	}
	for _, tc := range catchAllAddons {
		ct, ok := ResolveClusterType(tc.addonType, "any-topo")
		assert.True(t, ok, "addon %s should resolve with any topo", tc.addonType)
		assert.Equal(t, tc.expectedCT, ct)

		ct2, ok2 := ResolveClusterType(tc.addonType, "")
		assert.True(t, ok2, "addon %s should resolve with empty topo", tc.addonType)
		assert.Equal(t, tc.expectedCT, ct2)
	}
}

func TestResolveClusterType_UnknownAddon(t *testing.T) {
	_, ok := ResolveClusterType("unknown_addon", "some-topo")
	assert.False(t, ok)
}

func TestResolveClusterType_SurrealdbUnknownTopo(t *testing.T) {
	_, ok := ResolveClusterType("surrealdb", "unknown-topo")
	assert.False(t, ok)
}
