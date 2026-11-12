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

// SyncFilteredRequest 按条件同步存量集群到 DBM 的请求 vo。
type SyncFilteredRequest struct {
	K8sClusterName string   `json:"k8sClusterName" binding:"required"`
	Namespace      string   `json:"namespace"`
	ClusterNames   []string `json:"clusterNames" binding:"max=50"`
}

// SyncOneRequest 精确单集群同步到 DBM 的请求 vo。
// domain、instances、immuteDomain、region 完全由调用方手动指定，不读取也不回写本地 service，便于逐个验证。
type SyncOneRequest struct {
	K8sClusterName string   `json:"k8sClusterName" binding:"required"`
	Namespace      string   `json:"namespace" binding:"required"`
	ClusterName    string   `json:"clusterName" binding:"required"`
	Domain         string   `json:"domain" binding:"required"`
	Instances      []string `json:"instances" binding:"required,min=1,dive,required"`
	ImmuteDomain   string   `json:"immuteDomain" binding:"required"`
	Region         string   `json:"region" binding:"required"`
}
