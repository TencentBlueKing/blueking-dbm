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

import commentity "k8s-dbs/common/entity"

// K8sPodDetailRequest 集群实例详情请求结构体
type K8sPodDetailRequest struct {
	K8sClusterName    string `json:"k8sClusterName" binding:"required"`
	ClusterName       string `json:"clusterName" binding:"required"`
	Namespace         string `json:"namespace" binding:"required"`
	PodName           string `json:"podName" binding:"required"`
	commentity.BKAuth `json:",inline"`
}

// K8sPodDeleteRequest 封装 pod 删除请求结构体
type K8sPodDeleteRequest struct {
	K8sClusterName    string `json:"k8sClusterName"`
	ClusterName       string `json:"clusterName"`
	Namespace         string `json:"namespace"`
	PodName           string `json:"podName"`
	commentity.BKAuth `json:",inline"`
}
