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
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestAPIToIAMAction_AllWriteAPIsHaveMapping 验证需要 IAM 鉴权的写操作 API 都在 APIToIAMAction 映射中
func TestAPIToIAMAction_AllWriteAPIsHaveMapping(t *testing.T) {
	iamProtectedAPIs := []string{
		APIClusterCreate,
		APIClusterDelete,
		APIClusterUpdate,
		APIClusterPartialUpdate,
		APIClusterExpose,
		APIClusterStart,
		APIClusterStop,
		APIClusterRestart,
		APIClusterVScaling,
		APIClusterHScaling,
		APIClusterVExpansion,
		APIClusterUpgrade,
		APIK8sPodDelete,
		APIAddonInstall,
		APIAddonUninstall,
		APIAddonUpgrade,
	}

	for _, api := range iamProtectedAPIs {
		_, exists := APIToIAMAction[api]
		assert.True(t, exists, "API %s should have IAM action mapping", api)
	}
}

// TestClusterTypeToIAMPrefix_AllTypes 验证所有集群类型都有前缀映射
func TestClusterTypeToIAMPrefix_AllTypes(t *testing.T) {
	expectedTypes := []string{
		"k8s_surrealdb_ha",
		"k8s_surrealdb_single",
		"k8s_victoriametrics_ha",
		"k8s_risingwave_ha",
		"k8s_milvus_ha",
		"k8s_qdrant_ha",
		"k8s_greptimedb_ha",
	}

	for _, ct := range expectedTypes {
		prefix, exists := ClusterTypeToIAMPrefix[ct]
		assert.True(t, exists, "cluster type %s should have IAM prefix mapping", ct)
		assert.NotEmpty(t, prefix, "IAM prefix for cluster type %s should not be empty", ct)
	}
}

// TestAPIToIAMAction_ActionIDFormat 验证替换后的 action_id 不含 {type} 占位符
func TestAPIToIAMAction_ActionIDFormat(t *testing.T) {
	for apiName, template := range APIToIAMAction {
		for clusterType, prefix := range ClusterTypeToIAMPrefix {
			actionID := strings.Replace(template, "{type}", prefix, 1)
			assert.NotContains(t, actionID, "{type}",
				"after replacing, action_id should not contain {type}: api=%s, cluster=%s, result=%s",
				apiName, clusterType, actionID)
			assert.NotEmpty(t, actionID,
				"action_id should not be empty: api=%s, cluster=%s", apiName, clusterType)
		}
	}
}

// TestAddonManageAPIs_UseFixedActionID 验证 addon 操作使用统一的固定 action_id
func TestAddonManageAPIs_UseFixedActionID(t *testing.T) {
	addonAPIs := []string{
		APIAddonInstall,
		APIAddonUninstall,
		APIAddonUpgrade,
	}

	for _, apiName := range addonAPIs {
		actionID, exists := APIToIAMAction[apiName]
		assert.True(t, exists, "addon API %s should be in APIToIAMAction", apiName)
		assert.Equal(t, "k8s_addon_manage", actionID,
			"addon API %s should map to fixed 'k8s_addon_manage', not per-type template", apiName)
		assert.NotContains(t, actionID, "{type}",
			"addon action_id should not contain {type} placeholder")
	}
}
