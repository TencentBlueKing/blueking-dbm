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

package request

// CreateClusterRequest 创建集群请求
type CreateClusterRequest struct {
	Name         string `json:"name"`
	Alias        string `json:"alias"`
	BkBizID      uint64 `json:"bk_biz_id"`
	ClusterType  string `json:"cluster_type"`
	ImmuteDomain string `json:"immute_domain"`
	MajorVersion string `json:"major_version"`
	Phase        string `json:"phase"`
	Status       string `json:"status"`
	Region       string `json:"region"`
	Operator     string `json:"operator"`
}

// UpdateClusterRequest 更新集群请求（全量更新）
type UpdateClusterRequest struct {
	Name             string `json:"name"`
	Alias            string `json:"alias"`
	BkBizID          uint64 `json:"bk_biz_id"`
	ClusterType      string `json:"cluster_type"`
	ImmuteDomain     string `json:"immute_domain"`
	MajorVersion     string `json:"major_version"`
	Phase            string `json:"phase"`
	Status           string `json:"status"`
	Region           string `json:"region"`
	Operator         string `json:"operator"`
	ClusterEntryType string `json:"cluster_entry_type"`
}

// DeleteClusterRequest 删除集群请求
type DeleteClusterRequest struct {
	Name        string `json:"name"`
	BkBizID     uint64 `json:"bk_biz_id"`
	ClusterType string `json:"cluster_type"`
}
