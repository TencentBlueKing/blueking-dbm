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

import "k8s-dbs/core/entity"

// K8sNamespaceResponse k8s 的 namespace 创建返回结构体
type K8sNamespaceResponse struct {
	K8sClusterName string                `json:"k8sClusterName,omitempty"`
	Name           string                `json:"name" binding:"required"`
	Annotations    map[string]string     `json:"annotations,omitempty"`   // 可选注解
	Labels         map[string]string     `json:"labels,omitempty"`        // 可选标签
	ResourceQuota  *entity.ResourceQuota `json:"resourceQuota,omitempty"` // 可选资源配额
}
