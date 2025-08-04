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

package entity

// ComponentQueryParams 封装 component 请求参数
type ComponentQueryParams struct {
	K8sClusterName string `json:"k8sClusterName"`
	ClusterName    string `json:"clusterName"`
	Namespace      string `json:"namespace"`
	ComponentName  string `json:"componentName"`
}

// K8sPodDetailQueryParams 封装 pod detail 请求参数
type K8sPodDetailQueryParams struct {
	K8sClusterName string `json:"k8sClusterName"`
	ClusterName    string `json:"clusterName"`
	Namespace      string `json:"namespace"`
	PodName        string `json:"podName"`
}

// K8sPodLogQueryParams 封装 pod logs 请求参数
type K8sPodLogQueryParams struct {
	K8sClusterName string `json:"k8sClusterName" binding:"required"`
	ClusterName    string `json:"clusterName" binding:"required"`
	Namespace      string `json:"namespace" binding:"required"`
	PodName        string `json:"podName" binding:"required"`
	Container      string `json:"container,omitempty"`
}
