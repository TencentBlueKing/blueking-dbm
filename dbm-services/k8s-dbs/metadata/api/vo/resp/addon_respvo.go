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

import "time"

// K8sCrdAddonRespVo defines the response data structure of addon meta.
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
