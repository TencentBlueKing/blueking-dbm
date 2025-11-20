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

import (
	commonentity "k8s-dbs/common/entity"
	coreentity "k8s-dbs/core/entity"
)

// ClusterUpdatedRequest Receive request structure
type ClusterUpdatedRequest struct {
	K8sClusterName      string              `json:"k8sClusterName,omitempty" required:"true"`
	ClusterName         string              `json:"clusterName,omitempty" binding:"k8sReleaseName" msg:"集群名称格式不合法，只能包含小写字母、数字和连字符(-)，可以用点(.)分隔,且要求长度小于 53"` //nolint:lll
	Namespace           string              `json:"namespace,omitempty"`
	StorageAddonType    string              `json:"storageAddonType,omitempty"`
	ComponentList       []ComponentResource `json:"componentList,omitempty" binding:"dive"`
	commonentity.BKAuth `json:",inline"`
}

// ComponentResource component info
type ComponentResource struct {
	ComponentName string                 `json:"componentName,omitempty"`
	Env           map[string]interface{} `json:"env,omitempty"`
	Config        map[string]interface{} `json:"config,omitempty"`
}

// ComponentDetail 组件详情
type ComponentDetail struct {
	coreentity.Metadata `json:",inline"`
	Config              map[string]interface{} `json:"config,omitempty"`
}
