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

// CreateDomainRequest 创建域名记录请求
// 用于在 DBM DNS 服务中注册域名解析记录，同时在 ClusterEntry 表中创建对应的接入层条目
type CreateDomainRequest struct {
	BkCloudID   uint64   `json:"bk_cloud_id"`  // 云区域 ID
	BkBizID     uint64   `json:"bk_biz_id"`    // 业务 ID
	ClusterType string   `json:"cluster_type"` // 集群类型，如 k8s_vm、k8s_gt
	Name        string   `json:"name"`         // 集群名称
	Domain      string   `json:"domain"`       // 域名
	Instances   []string `json:"instances"`    // 实例列表，格式：ip#port
	Role        string   `json:"role"`         // 入口角色，默认 master_entry
	Operator    string   `json:"operator"`     // 操作人
}

// GetDomainRequest 查询域名解析记录请求
type GetDomainRequest struct {
	BkCloudID   uint64 `json:"bk_cloud_id"`
	BkBizID     uint64 `json:"bk_biz_id"`
	ClusterType string `json:"cluster_type"`
	Name        string `json:"name"`
	Domain      string `json:"domain"`
}

// DeleteDomainRequest 删除域名解析记录请求
type DeleteDomainRequest struct {
	BkCloudID   uint64 `json:"bk_cloud_id"`
	BkBizID     uint64 `json:"bk_biz_id"`
	ClusterType string `json:"cluster_type"`
	Name        string `json:"name"`
	Domain      string `json:"domain"`
	Operator    string `json:"operator"`
}
