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

import "strings"

const iamActionTypePlaceholder = "{type}"

// APIToIAMAction 将 API 名称常量映射到 IAM action_id 模板。
// {type} 占位符在运行时替换为 ClusterTypeToIAMPrefix 中的值，
// 替换后得到完整 action_id，如 k8s_surrealdb_apply。
// 生成实际 id 时必须走 ResolveIAMActionID，以处理例外命名。
//
// 不在此映射中的 API 路由会跳过 IAM 鉴权（中间件直接放行）。
var APIToIAMAction = map[string]string{
	APIClusterCreate:        "{type}_apply",
	APIClusterDelete:        "{type}_destroy",
	APIClusterStart:         "{type}_enable_disable",
	APIClusterStop:          "{type}_enable_disable",
	APIClusterUpdate:        "{type}_manage",
	APIClusterPartialUpdate: "{type}_manage",
	APIClusterExpose:        "{type}_manage",
	APIClusterRestart:       "{type}_manage",
	APIClusterVScaling:      "{type}_manage",
	APIClusterHScaling:      "{type}_manage",
	APIClusterVExpansion:    "{type}_manage",
	APIClusterUpgrade:       "{type}_manage",
	APIK8sPodDelete:         "{type}_manage",
	APIAddonInstall:         "k8s_addon_manage",
	APIAddonUninstall:       "k8s_addon_manage",
	APIAddonUpgrade:         "k8s_addon_manage",
}

// iamActionIDOverrides 记录不符合「{IAM 前缀}_{操作后缀}」规则的例外 action_id。
// key 为 (IAM 前缀, 操作后缀)，value 必须与 DBM ActionEnum 中注册的 id 一致。
// 背景：IAM 限制 action id 最长 32 字符，k8s_victoriametrics_enable_disable 超长，
// DBM 侧（dbm-ui/backend/iam_app/dataclass/actions.py）注册为 k8s_vm_enable_disable。
var iamActionIDOverrides = map[string]map[string]string{
	"k8s_victoriametrics": {
		"enable_disable": "k8s_vm_enable_disable",
	},
}

// ResolveIAMActionID 生成实际注册在 IAM 的 action_id。
// 默认把模板中的 {type} 替换为 iamPrefix（如 k8s_surrealdb_apply）；
// 命中 iamActionIDOverrides 时返回例外 id（如 k8s_vm_enable_disable）。
func ResolveIAMActionID(iamPrefix, actionTemplate string) string {
	suffix := strings.TrimPrefix(actionTemplate, iamActionTypePlaceholder+"_")
	if overrides, ok := iamActionIDOverrides[iamPrefix]; ok {
		if actionID, ok := overrides[suffix]; ok {
			return actionID
		}
	}
	return strings.Replace(actionTemplate, iamActionTypePlaceholder, iamPrefix, 1)
}
