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

// AddonIAMEntry 定义 addon 在 IAM 鉴权维度的映射。
type AddonIAMEntry struct {
	AddonType   string // DB 中的 addon_type 值，如 "surrealdb"
	ClusterType string // IAM cluster_type，如 "k8s_surrealdb"
}

// addonIAMRegistry 是 IAM 鉴权维度的 addon 注册表。
// 新增 addon 只需在此追加一行，派生 map 自动更新。
var addonIAMRegistry = []AddonIAMEntry{
	{"surrealdb", "k8s_surrealdb"},
	{"victoriametrics", "k8s_victoriametrics"},
	{"risingwave", "k8s_risingwave"},
	{"greptimedb", "k8s_greptimedb"},
	{"milvus", "k8s_milvus"},
	{"qdrant", "k8s_qdrant"},
}

// AddonTypeToIAMClusterType 从 DB addon_type 映射到 IAM cluster_type。
// 例: "surrealdb" -> "k8s_surrealdb"
var AddonTypeToIAMClusterType map[string]string

// ClusterTypeToIAMPrefix 从 IAM cluster_type 映射到 IAM action 前缀。
// 当前为 identity 映射（"k8s_surrealdb" -> "k8s_surrealdb"），保持中间件接口不变。
var ClusterTypeToIAMPrefix map[string]string

func init() {
	AddonTypeToIAMClusterType = make(map[string]string, len(addonIAMRegistry))
	ClusterTypeToIAMPrefix = make(map[string]string, len(addonIAMRegistry))

	for _, entry := range addonIAMRegistry {
		AddonTypeToIAMClusterType[entry.AddonType] = entry.ClusterType
		ClusterTypeToIAMPrefix[entry.ClusterType] = entry.ClusterType
	}
}
