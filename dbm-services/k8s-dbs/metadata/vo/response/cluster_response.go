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

import (
	"encoding/json"
	commtypes "k8s-dbs/common/types"
)

// K8sCrdClusterResponse response vo 定义
type K8sCrdClusterResponse struct {
	ID                  uint64                      `json:"id"`
	AddonInfo           *ClusterAddonResponse       `json:"addonInfo"`
	AddonClusterVersion string                      `json:"addonClusterVersion"`
	ServiceVersion      string                      `json:"serviceVersion"`
	TopoName            string                      `json:"topoName"`
	TopoNameAlias       string                      `json:"topoNameAlias"`
	K8sClusterConfig    *K8sClusterConfigResponse   `json:"k8sClusterConfig"`
	RequestID           string                      `json:"requestId"`
	ClusterName         string                      `json:"clusterName"`
	ClusterAlias        string                      `json:"clusterAlias"`
	Namespace           string                      `json:"namespace"`
	BkBizID             uint64                      `json:"bkBizId"`
	BkBizName           string                      `json:"bkBizName"`
	BkAppAbbr           string                      `json:"bkAppAbbr"`
	BkAppCode           string                      `json:"bkAppCode"`
	BkBizTitle          string                      `json:"bkBizTitle"`
	Tags                []*K8sCrdClusterTagResponse `json:"tags"`
	Status              string                      `json:"status"`
	Description         string                      `json:"description"`
	CreatedBy           string                      `json:"createdBy"`
	CreatedAt           commtypes.JSONDatetime      `json:"createdAt"`
	UpdatedBy           string                      `json:"updatedBy"`
	UpdatedAt           commtypes.JSONDatetime      `json:"updatedAt"`
}

// ClusterAddonResponse 定义集群详情中 Addon 返回数据结构
type ClusterAddonResponse struct {
	ID                   uint64                  `json:"id"`
	AddonName            string                  `json:"addonName"`
	AddonCategory        string                  `json:"addonCategory"`
	AddonType            string                  `json:"addonType"`
	AddonVersion         string                  `json:"addonVersion"`
	RecommendedVersion   string                  `json:"recommendedVersion"`
	SupportedVersions    string                  `json:"supportedVersions"`
	RecommendedAcVersion string                  `json:"recommendedAcVersion"`
	SupportedAcVersions  string                  `json:"supportedAcVersions"`
	Topologies           string                  `json:"topologies"`
	Topology             ClusterTopologyResponse `json:"topology"`
	Active               bool                    `json:"active"`
	Description          string                  `json:"description"`
}

// MarshalJSON 自定义 ClusterAddonResponse JSON 序列化逻辑
func (k K8sCrdClusterResponse) MarshalJSON() ([]byte, error) {
	var topologiesArray []ClusterTopologyResponse
	err := json.Unmarshal([]byte(k.AddonInfo.Topologies), &topologiesArray)
	if err != nil {
		return nil, err
	}
	if len(topologiesArray) > 0 {
		for _, topo := range topologiesArray {
			topo.Name = k.TopoName
			k.AddonInfo.Topology = topo
			break
		}
	}

	output := map[string]interface{}{
		"id": k.ID,
		"addonInfo": map[string]interface{}{
			"id":            k.AddonInfo.ID,
			"active":        k.AddonInfo.Active,
			"addonCategory": k.AddonInfo.AddonCategory,
			"addonType":     k.AddonInfo.AddonType,
			"addonVersion":  k.AddonInfo.AddonVersion,
			"addonName":     k.AddonInfo.AddonName,
			"topology":      k.AddonInfo.Topology,
		},
		"addonClusterVersion": k.AddonClusterVersion,
		"serviceVersion":      k.ServiceVersion,
		"topoName":            k.TopoName,
		"topoNameAlias":       k.TopoNameAlias,
		"k8sClusterConfig":    k.K8sClusterConfig,
		"requestId":           k.RequestID,
		"clusterName":         k.ClusterName,
		"clusterAlias":        k.ClusterAlias,
		"namespace":           k.Namespace,
		"bkBizId":             k.BkBizID,
		"bkBizName":           k.BkBizName,
		"bkAppAbbr":           k.BkAppAbbr,
		"bkAppCode":           k.BkAppCode,
		"bkBizTitle":          k.BkBizTitle,
		"tags":                k.Tags,
		"status":              k.Status,
		"createdBy":           k.CreatedBy,
		"createdAt":           k.CreatedAt,
		"updatedBy":           k.UpdatedBy,
		"updatedAt":           k.UpdatedAt,
		"description":         k.Description,
	}
	return json.Marshal(output)
}

// ClusterTopologyResponse 定义集群详情 topology 返回数据结构
type ClusterTopologyResponse struct {
	Name        string                    `json:"name"`
	IsDefault   bool                      `json:"isDefault"`
	Description string                    `json:"description"`
	Components  []*AddonComponentResponse `json:"components"`
}

// AddonComponentResponse 定义 topology component 返回数据结构
type AddonComponentResponse struct {
	Name        string `json:"name"`
	Alias       string `json:"alias"`
	Description string `json:"description"`
}
