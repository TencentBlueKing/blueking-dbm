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

import commtypes "k8s-dbs/common/types"

// K8sCrdStorageAddonEntity addon entity 定义
type K8sCrdStorageAddonEntity struct {
	ID                   uint64                 `json:"id"`
	AddonName            string                 `json:"addonName"`
	AddonCategory        string                 `json:"addonCategory"`
	AddonType            string                 `json:"addonType"`
	AddonVersion         string                 `json:"addonVersion"`
	Topologies           string                 `json:"topologies"`
	RecommendedVersion   string                 `json:"recommendedVersion"`
	SupportedVersions    string                 `json:"supportedVersions"`
	RecommendedAcVersion string                 `json:"recommendedAcVersion"`
	SupportedAcVersions  string                 `json:"supportedAcVersions"`
	Releases             string                 `json:"releases"`
	Active               bool                   `json:"active"`
	Description          string                 `json:"description"`
	CreatedBy            string                 `json:"createdBy"`
	CreatedAt            commtypes.JSONDatetime `json:"createdAt"`
	UpdatedBy            string                 `json:"updatedBy"`
	UpdatedAt            commtypes.JSONDatetime `json:"updatedAt"`
}

// ClusterTopology 集群拓扑结构
type ClusterTopology struct {
	Name       string              `json:"name"`
	Default    bool                `json:"default"`
	Components []*ClusterComponent `json:"components"`
}

// ClusterComponent 拓扑关联的组件信息
type ClusterComponent struct {
	Name string `json:"name"`
}

// AddonVersionEntity addon version entity 定义
type AddonVersionEntity struct {
	AddonVersion      string `json:"addonVersion"`
	SupportedVersions string `json:"supportedVersions"`
}
