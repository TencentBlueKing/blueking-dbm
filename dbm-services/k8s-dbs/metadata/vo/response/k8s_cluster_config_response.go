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

// K8sClusterConfigResponse response vo 定义
type K8sClusterConfigResponse struct {
	ID          uint64 `json:"id"`
	ClusterName string `json:"clusterName"`
	IsPublic    bool   `json:"isPublic"`
	RegionName  string `json:"regionName"`
	RegionCode  string `json:"regionCode"`
	VpcID       string `json:"vpcID"`
	Provider    string `json:"provider"`
	Description string `json:"description"`
}

// RegionResp 区域信息响应结构体
type RegionResp struct {
	RegionName     string           `json:"regionName"`
	RegionCode     string           `json:"regionCode"`
	Provider       string           `json:"provider"`
	K8sClusterList []K8sClusterResp `json:"k8sClusterList"`
}

// K8sClusterResp k8s 集群信息结构体
type K8sClusterResp struct {
	ClusterName  string `json:"clusterName"`
	ClusterAlias string `json:"clusterAlias"`
	VpcID        string `json:"vpcID"`
}
