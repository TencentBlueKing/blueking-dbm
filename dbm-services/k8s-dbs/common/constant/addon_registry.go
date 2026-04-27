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

import "slices"

// AddonIAMEntry 定义 addon 在 IAM 鉴权维度的映射。
// 同一 AddonType 可注册多条（按 Topologies 区分 HA/Single），共享同一 IAMPrefix。
type AddonIAMEntry struct {
	AddonType      string   // DB 中的 addon_type，如 "surrealdb"
	DbmClusterType string   // DBM cluster_type，如 "k8s_surrealdb_ha"
	IAMPrefix      string   // IAM action 前缀（共享维度），如 "k8s_surrealdb"
	Topologies     []string // 匹配的 topology 名称；nil 表示匹配所有（catch-all）
}

// addonIAMRegistry 是 IAM 鉴权维度的 addon 注册表。
// 新增 addon 只需在此追加一行，派生 map 自动更新。
var addonIAMRegistry = []AddonIAMEntry{
	{"surrealdb", "k8s_surrealdb_ha", "k8s_surrealdb", []string{"surreal-tikv"}},
	{"surrealdb", "k8s_surrealdb_single", "k8s_surrealdb", []string{"surreal-rocksdb", "surreal-memory"}},
	{"victoriametrics", "k8s_victoriametrics_ha", "k8s_victoriametrics", nil},
	{"risingwave", "k8s_risingwave_ha", "k8s_risingwave", nil},
	{"greptimedb", "k8s_greptimedb_ha", "k8s_greptimedb", nil},
	{"milvus", "k8s_milvus_ha", "k8s_milvus", nil},
	{"qdrant", "k8s_qdrant_ha", "k8s_qdrant", nil},
}

// ClusterTypeToIAMPrefix 从 cluster_type 映射到 IAM action 前缀。
// 多对一映射：如 "k8s_surrealdb_ha" 和 "k8s_surrealdb_single" 都映射到 "k8s_surrealdb"。
var ClusterTypeToIAMPrefix map[string]string

func init() {
	ClusterTypeToIAMPrefix = make(map[string]string, len(addonIAMRegistry))
	for _, entry := range addonIAMRegistry {
		ClusterTypeToIAMPrefix[entry.DbmClusterType] = entry.IAMPrefix
	}
}

// ResolveClusterType 根据 addonType 和 topoName 解析出 cluster_type。
// Topologies 为 nil 的条目匹配任意 topoName（catch-all）。
func ResolveClusterType(addonType, topoName string) (string, bool) {
	for _, entry := range addonIAMRegistry {
		if entry.AddonType != addonType {
			continue
		}
		if entry.Topologies == nil || slices.Contains(entry.Topologies, topoName) {
			return entry.DbmClusterType, true
		}
	}
	return "", false
}
