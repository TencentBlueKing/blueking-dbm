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

import (
	"encoding/json"
	"time"
)

// K8sCrdAddonRespVo response vo 定义
type K8sCrdAddonRespVo struct {
	ID                   uint64    `json:"id"`
	AddonName            string    `json:"addonName"`
	AddonCategory        string    `json:"addonCategory"`
	AddonType            string    `json:"addonType"`
	AddonVersion         string    `json:"addonVersion"`
	RecommendedVersion   string    `json:"recommendedVersion"`
	SupportedVersions    string    `json:"supportedVersions"`
	RecommendedAcVersion string    `json:"recommendedAcVersion"`
	SupportedAcVersions  string    `json:"supportedAcVersions"`
	Topologies           string    `json:"topologies"`
	Releases             string    `json:"releases"`
	Active               bool      `json:"active"`
	Description          string    `json:"description"`
	CreatedBy            string    `json:"createdBy"`
	CreatedAt            time.Time `json:"createdAt"`
	UpdatedBy            string    `json:"updatedBy"`
	UpdatedAt            time.Time `json:"updatedAt"`
}

// MarshalJSON 自定义 K8sCrdAddonRespVo JSON 序列化逻辑
func (k K8sCrdAddonRespVo) MarshalJSON() ([]byte, error) {
	var topologiesArray []map[string]any
	err := json.Unmarshal([]byte(k.Topologies), &topologiesArray)
	if err != nil {
		return nil, err
	}
	var releasesArray []map[string]any
	err = json.Unmarshal([]byte(k.Releases), &releasesArray)
	if err != nil {
		return nil, err
	}
	var supportedVersionsArray []string
	err = json.Unmarshal([]byte(k.SupportedVersions), &supportedVersionsArray)
	if err != nil {
		return nil, err
	}
	var supportedAcVersionsArray []string
	err = json.Unmarshal([]byte(k.SupportedAcVersions), &supportedAcVersionsArray)
	if err != nil {
		return nil, err
	}
	output := map[string]interface{}{
		"id":                   k.ID,
		"addonName":            k.AddonName,
		"addonCategory":        k.AddonCategory,
		"addonType":            k.AddonType,
		"addonVersion":         k.AddonVersion,
		"recommendedVersion":   k.RecommendedVersion,
		"supportedVersions":    supportedVersionsArray,
		"recommendedAcVersion": k.RecommendedAcVersion,
		"supportedAcVersions":  supportedAcVersionsArray,
		"topologies":           topologiesArray,
		"releases":             releasesArray,
		"active":               k.Active,
		"description":          k.Description,
		"createdBy":            k.CreatedBy,
		"createdAt":            k.CreatedAt,
		"updatedBy":            k.UpdatedBy,
		"updatedAt":            k.UpdatedAt,
	}
	return json.Marshal(output)
}
