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

func TestAddonIAMRegistry_NoDuplicateAddonType(t *testing.T) {
	seen := make(map[string]bool)
	for _, entry := range addonIAMRegistry {
		assert.False(t, seen[entry.AddonType],
			"duplicate AddonType in registry: %s", entry.AddonType)
		seen[entry.AddonType] = true
	}
}

func TestAddonIAMRegistry_NoDuplicateClusterType(t *testing.T) {
	seen := make(map[string]bool)
	for _, entry := range addonIAMRegistry {
		assert.False(t, seen[entry.ClusterType],
			"duplicate ClusterType in registry: %s", entry.ClusterType)
		seen[entry.ClusterType] = true
	}
}

func TestAddonIAMRegistry_AllSixAddonsPresent(t *testing.T) {
	expectedAddons := []string{
		"surrealdb", "victoriametrics", "risingwave",
		"greptimedb", "milvus", "qdrant",
	}

	for _, addon := range expectedAddons {
		_, exists := AddonTypeToIAMClusterType[addon]
		assert.True(t, exists, "addon %s should be in registry", addon)
	}
	assert.Equal(t, len(expectedAddons), len(addonIAMRegistry),
		"registry should have exactly %d entries", len(expectedAddons))
}

func TestAddonIAMRegistry_QdrantMapping(t *testing.T) {
	ct, exists := AddonTypeToIAMClusterType["qdrant"]
	assert.True(t, exists, "qdrant should be in AddonTypeToIAMClusterType")
	assert.Equal(t, "k8s_qdrant", ct)

	prefix, exists := ClusterTypeToIAMPrefix["k8s_qdrant"]
	assert.True(t, exists, "k8s_qdrant should be in ClusterTypeToIAMPrefix")
	assert.Equal(t, "k8s_qdrant", prefix)
}

func TestAddonTypeToIAMClusterType_CorrectMappings(t *testing.T) {
	expected := map[string]string{
		"surrealdb":       "k8s_surrealdb",
		"victoriametrics": "k8s_victoriametrics",
		"risingwave":      "k8s_risingwave",
		"greptimedb":      "k8s_greptimedb",
		"milvus":          "k8s_milvus",
		"qdrant":          "k8s_qdrant",
	}

	for addonType, expectedCT := range expected {
		ct, exists := AddonTypeToIAMClusterType[addonType]
		assert.True(t, exists, "addon %s should be in map", addonType)
		assert.Equal(t, expectedCT, ct, "addon %s should map to %s", addonType, expectedCT)
	}
}

func TestClusterTypeToIAMPrefix_IdentityMapping(t *testing.T) {
	// ClusterTypeToIAMPrefix should be identity mapping for all entries
	for _, entry := range addonIAMRegistry {
		prefix, exists := ClusterTypeToIAMPrefix[entry.ClusterType]
		assert.True(t, exists)
		assert.Equal(t, entry.ClusterType, prefix,
			"ClusterTypeToIAMPrefix should be identity mapping for %s", entry.ClusterType)
	}
}
