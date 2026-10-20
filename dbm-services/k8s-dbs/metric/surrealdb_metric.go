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

package metric

// SurrealDBClusterMetricFetcher 通过 Kubelet Summary API 获取 SurrealDB 存储用量。
// 集群由 surreal/tikv/pd 多组件构成，调用方按 Pod 维度分别传参即可。
type SurrealDBClusterMetricFetcher struct {
	BaseKubeletMetricFetcher
}

// NewSurrealDBClusterMetricFetcher 创建 SurrealDBClusterMetricFetcher 实例
func NewSurrealDBClusterMetricFetcher() *SurrealDBClusterMetricFetcher {
	return &SurrealDBClusterMetricFetcher{
		BaseKubeletMetricFetcher: NewBaseKubeletMetricFetcher("SurrealDB"),
	}
}
