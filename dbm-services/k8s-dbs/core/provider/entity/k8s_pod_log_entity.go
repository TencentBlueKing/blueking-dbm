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

// K8sPodLogEntity k8s 的 pod 日志请求
type K8sPodLogEntity struct {
	K8sClusterName string `json:"k8sClusterName" binding:"required"`
	ClusterName    string `json:"clusterName" binding:"required"`
	Namespace      string `json:"namespace" binding:"required"`
	PodName        string `json:"podName" binding:"required"`
	Container      string `json:"container,omitempty"`
}
