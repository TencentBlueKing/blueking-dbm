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

package resp

// ClusterDetailRespVo cluster detail response
type ClusterDetailRespVo struct {
	Metadata      ClusterMeta          `json:"metadata,omitempty"`
	Spec          ClusterSpec          `json:"spec,omitempty"`
	ClusterStatus *ClusterStatusRespVo `json:"status,omitempty"`
}

// ClusterMeta the metadata of cluster
type ClusterMeta struct {
	ClusterName string `json:"clusterName,omitempty"`
	Namespace   string `json:"namespace,omitempty"`
	Kind        string `json:"kind,omitempty"`
}

// ClusterSpec the spec of cluster
type ClusterSpec struct {
	Version       string            `json:"version,omitempty"`
	TopoName      string            `json:"topoName,omitempty"`
	ComponentList []ComponentDetail `json:"componentList,omitempty"`
}

// ComponentDetail the detail info of component
type ComponentDetail struct {
	ComponentName string                 `json:"componentName,omitempty"`
	ComponentDef  string                 `json:"componentDef,omitempty"`
	Version       string                 `json:"version,omitempty"`
	Replicas      int32                  `json:"replicas,omitempty"`
	Env           map[string]interface{} `json:"env,omitempty"`
	Request       *ResourceDetail        `json:"request,omitempty"`
	Limit         *ResourceDetail        `json:"limit,omitempty"`
	Storage       string                 `json:"storage,omitempty"`
	Args          map[string]interface{} `json:"args,omitempty"`
}

// ResourceDetail the resource of component
type ResourceDetail struct {
	CPU    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
}
