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
		"k8s_victoriametrics_cluster",
		"k8s_victoriametrics_select",
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

// TestAPIToIAMAction_ActionIDFormat 验证生成的 action_id 合法且符合 IAM 长度限制
func TestAPIToIAMAction_ActionIDFormat(t *testing.T) {
	for apiName, template := range APIToIAMAction {
		for clusterType, prefix := range ClusterTypeToIAMPrefix {
			actionID := ResolveIAMActionID(prefix, template)
			assert.NotContains(t, actionID, "{type}",
				"after resolving, action_id should not contain {type}: api=%s, cluster=%s, result=%s",
				apiName, clusterType, actionID)
			assert.NotEmpty(t, actionID,
				"action_id should not be empty: api=%s, cluster=%s", apiName, clusterType)
			assert.True(t, len(actionID) <= 32,
				"IAM action_id 不得超过 32 字符: api=%s, cluster=%s, action=%s",
				apiName, clusterType, actionID)
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

// TestResolveIAMActionID_VictoriaMetricsEnableDisable 验证 VM 启停命中例外命名
func TestResolveIAMActionID_VictoriaMetricsEnableDisable(t *testing.T) {
	for _, clusterType := range []string{"k8s_victoriametrics_cluster", "k8s_victoriametrics_select"} {
		prefix := ClusterTypeToIAMPrefix[clusterType]
		for _, apiName := range []string{APIClusterStart, APIClusterStop} {
			assert.Equal(t, "k8s_vm_enable_disable", ResolveIAMActionID(prefix, APIToIAMAction[apiName]),
				"cluster=%s, api=%s should use abbreviated action_id", clusterType, apiName)
		}
	}
}

// TestResolveIAMActionID_OtherActions 验证例外命名不影响其它操作与其它存储
func TestResolveIAMActionID_OtherActions(t *testing.T) {
	vmPrefix := ClusterTypeToIAMPrefix["k8s_victoriametrics_cluster"]
	for apiName, expected := range map[string]string{
		APIClusterCreate: "k8s_victoriametrics_apply",
		APIClusterDelete: "k8s_victoriametrics_destroy",
		APIClusterUpdate: "k8s_victoriametrics_manage",
		APIAddonInstall:  "k8s_addon_manage",
	} {
		assert.Equal(t, expected, ResolveIAMActionID(vmPrefix, APIToIAMAction[apiName]), "api=%s", apiName)
	}

	for clusterType, prefix := range ClusterTypeToIAMPrefix {
		if prefix == "k8s_victoriametrics" {
			continue
		}
		assert.Equal(t, prefix+"_enable_disable", ResolveIAMActionID(prefix, APIToIAMAction[APIClusterStart]),
			"cluster=%s should keep the default action_id", clusterType)
	}
}
