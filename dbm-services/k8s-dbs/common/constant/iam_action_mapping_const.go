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

// APIToIAMAction 将 API 名称常量映射到 IAM action_id 模板。
// {type} 占位符在运行时替换为 ClusterTypeToIAMPrefix 中的值，
// 替换后得到完整 action_id，如 k8s_surrealdb_apply。
//
// 不在此映射中的 API 路由会跳过 IAM 鉴权（中间件直接放行）。
var APIToIAMAction = map[string]string{
	APIClusterCreate:        "{type}_apply",
	APIClusterDelete:        "{type}_destroy",
	APIClusterUpdate:        "{type}_modify",
	APIClusterPartialUpdate: "{type}_modify",
	APIClusterExpose:        "{type}_modify",
	APIClusterStart:         "{type}_start",
	APIClusterStop:          "{type}_stop",
	APIClusterRestart:       "{type}_restart",
	APIClusterVScaling:      "{type}_scale",
	APIClusterHScaling:      "{type}_scale",
	APIClusterVExpansion:    "{type}_scale",
	APIClusterUpgrade:       "{type}_upgrade",
	APIK8sPodDelete:         "{type}_pod_delete",
	APIAddonInstall:         "k8s_addon_manage",
	APIAddonUninstall:       "k8s_addon_manage",
	APIAddonUpgrade:         "k8s_addon_manage",
}
