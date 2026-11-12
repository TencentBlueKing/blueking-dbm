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

package response

// SyncLegacyResponse 存量集群同步到 DBM 的汇总结果响应 vo。
type SyncLegacyResponse struct {
	Total   int                        `json:"total"`
	Success int                        `json:"success"`
	Failed  int                        `json:"failed"`
	Details []SyncLegacyDetailResponse `json:"details"`
}

// SyncLegacyDetailResponse 单个集群同步结果响应 vo。
type SyncLegacyDetailResponse struct {
	ClusterID    uint64 `json:"clusterId"`
	ClusterName  string `json:"clusterName"`
	Status       string `json:"status"`
	DbmClusterID uint64 `json:"dbmClusterId,omitempty"`
	Error        string `json:"error,omitempty"`
}
