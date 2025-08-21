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

// K8sSvcEntity k8s svc entity
type K8sSvcEntity struct {
	K8sClusterName string `json:"k8sClusterName" binding:"required"`
	ClusterName    string `json:"clusterName" binding:"required"`
	Namespace      string `json:"namespace" binding:"required"`
	ComponentName  string `json:"componentName"`
}

// K8sInternalSvcInfo 封装 Service 内部访问信息
type K8sInternalSvcInfo struct {
	Name      string     `json:"name"`
	Namespace string     `json:"namespace"`
	FQDN      string     `json:"fqdn"`
	Ports     []PortInfo `json:"ports"`
}

// PortInfo 表示单个端口的信息（内部访问）
type PortInfo struct {
	Port     int32  `json:"port"`
	Protocol string `json:"protocol"`
	FullAddr string `json:"fullAddr"`
}

// K8sExternalSvcInfo 封装 LoadBalancer 的外部访问信息
type K8sExternalSvcInfo struct {
	Name      string         `json:"name"`
	Namespace string         `json:"namespace"`
	Hostname  string         `json:"hostname,omitempty"` // 外部域名（仅 LoadBalancer 有）
	Ports     []ExternalPort `json:"ports,omitempty"`    // 外部端口信息（仅 LoadBalancer 有）
}

// ExternalPort 表示单个外部端口的信息
type ExternalPort struct {
	Port     int32  `json:"port"`     // Service 暴露的端口
	Protocol string `json:"protocol"` // 协议（TCP/UDP）
	FullAddr string `json:"fullAddr"` // 外部完整地址（IP/Hostname:Port）
}
