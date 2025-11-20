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

// K8sPodDetail k8s pod 详情结构体
type K8sPodDetail struct {
	K8sClusterName string `json:"k8sClusterName"`
	ClusterName    string `json:"clusterName" `
	Namespace      string `json:"namespace"`
	ComponentName  string `json:"componentName"`
	*Pod           `json:",inline"`
	Manifest       string `json:"manifest"`
}

// K8sPodDelete k8s pod 删除结构体
type K8sPodDelete struct {
	K8sClusterName string `json:"k8sClusterName" binding:"required"`
	ClusterName    string `json:"clusterName" binding:"required"`
	Namespace      string `json:"namespace" binding:"required"`
	PodName        string `json:"podName" binding:"required"`
}
