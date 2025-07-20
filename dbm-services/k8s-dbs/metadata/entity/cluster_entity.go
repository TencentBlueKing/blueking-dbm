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

import (
	commtypes "k8s-dbs/common/types"

	corev1 "k8s.io/api/core/v1"
)

// K8sCrdClusterEntity cluster entity 定义
type K8sCrdClusterEntity struct {
	ID                  uint64                    `json:"id"`
	AddonID             uint64                    `json:"addonId"`
	AddonClusterVersion string                    `json:"addonClusterVersion"`
	AddonInfo           *K8sCrdStorageAddonEntity `json:"addonInfo"`
	TopoName            string                    `json:"topoName"`
	K8sClusterConfigID  uint64                    `json:"k8sClusterConfigId"`
	K8sClusterConfig    *K8sClusterConfigEntity   `json:"k8sClusterConfig"`
	RequestID           string                    `json:"requestId"`
	ClusterName         string                    `json:"clusterName"`
	ClusterAlias        string                    `json:"clusterAlias"`
	Namespace           string                    `json:"namespace"`
	BkBizID             uint64                    `json:"bkBizId"`
	BkBizName           string                    `json:"bkBizName"`
	BkAppAbbr           string                    `json:"bkAppAbbr"`
	BkAppCode           string                    `json:"bkAppCode"`
	Tags                []*K8sCrdClusterTagEntity `json:"tags"`
	Status              string                    `json:"status"`
	Description         string                    `json:"description"`
	CreatedBy           string                    `json:"createdBy"`
	CreatedAt           commtypes.JSONDatetime    `json:"createdAt"`
	UpdatedBy           string                    `json:"updatedBy"`
	UpdatedAt           commtypes.JSONDatetime    `json:"updatedAt"`
}

// ClusterTopologyEntity cluster topology entity 定义
type ClusterTopologyEntity struct {
	AddonName      string                     `json:"addonName"`
	AddonCategory  string                     `json:"addonCategory"`
	AddonType      string                     `json:"addonType"`
	AddonVersion   string                     `json:"addonVersion"`
	K8sClusterName string                     `json:"k8sClusterName"`
	ClusterName    string                     `json:"clusterName"`
	ClusterAlias   string                     `json:"clusterAlias"`
	Namespace      string                     `json:"namespace"`
	IsDefault      bool                       `json:"isDefault"`
	TopoName       string                     `json:"topoName"`
	Status         string                     `json:"status"`
	Components     []*TopologyComponentEntity `json:"components"`
	Relations      []*ComponentRelationEntity `json:"relations"`
	Description    string                     `json:"description"`
}

// TopologyComponentEntity topology 组件定义
type TopologyComponentEntity struct {
	Name        string                `json:"name"`
	Alias       string                `json:"alias"`
	Description string                `json:"description"`
	Instances   []*ComponentPodEntity `json:"instances"`
}

// ComponentPodEntity topology 组件包含的实例 pod 定义
type ComponentPodEntity struct {
	PodName     string                 `json:"podName"`
	Status      corev1.PodPhase        `json:"status"`
	CreatedTime commtypes.JSONDatetime `json:"createdTime"`
}

// ComponentRelationEntity 组件关系描述
type ComponentRelationEntity struct {
	Name      string `json:"name"`
	TypeName  string `json:"typeName"`
	TypeAlias string `json:"typeAlias"`
	From      string `json:"from"`
	To        string `json:"to"`
	Direction string `json:"direction"`
}
