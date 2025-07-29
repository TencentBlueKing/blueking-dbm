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
	coreentity "k8s-dbs/common/entity"

	"k8s.io/apimachinery/pkg/api/resource"
)

// ClusterInstallRequest 集群安装完整配置
type ClusterInstallRequest struct {
	BasicInfo         BasicInfo        `json:"basicInfo"`
	ResourceConfig    ResourceConfig   `json:"resourceConfig"`
	DeploymentEnv     DeploymentEnv    `json:"deploymentEnv"`
	AdvancedSettings  AdvancedSettings `json:"advancedSettings"`
	coreentity.BKAuth `json:",inline"`
}

// BasicInfo 集群基本信息
type BasicInfo struct {
	ClusterName      string   `json:"clusterName" binding:"required"`
	ClusterAlias     string   `json:"clusterAlias"`
	StorageAddonType string   `json:"storageAddonType"`
	BkBizID          uint64   `json:"bkBizId"`
	BkBizName        string   `json:"bkBizName"`
	BkAppAbbr        string   `json:"bkAppAbbr"`
	Tags             []string `json:"tags"`
	Description      string   `json:"description"`
}

// ResourceConfig 集群资源设置
type ResourceConfig struct {
	Version       []string    `json:"version"`
	TopoName      string      `json:"topoName"`
	ComponentList []Component `json:"componentList"`
}

// Component 组件资源设置
type Component struct {
	ComponentName string            `json:"componentName"`
	Replicas      int32             `json:"replicas"`
	RequestCPU    resource.Quantity `json:"requestCpu"`
	RequestMemory resource.Quantity `json:"requestMemory"`
	StorageNodes  string            `json:"storageNodes,omitempty"` // 使用omitempty表示该字段是可选的
	Storage       resource.Quantity `json:"storage,omitempty"`      // 使用omitempty表示该字段是可选的
}

// DeploymentEnv 部署环境设置
type DeploymentEnv struct {
	DeployType     string `json:"deployType"`
	ClusterType    string `json:"clusterType"`
	Region         string `json:"region"`
	K8sClusterName string `json:"k8sClusterName"`
}

// AdvancedSettings 高级部署设置
type AdvancedSettings struct {
	TerminationPolicy string            `json:"terminationPolicy"`
	Labels            map[string]string `json:"labels"`
}
