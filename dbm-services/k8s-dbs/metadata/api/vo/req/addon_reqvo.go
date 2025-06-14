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

package req

import "time"

// K8sCrdAddonReqVo represents the request data structure of addon meta.
type K8sCrdAddonReqVo struct {
	AddonName            string    `json:"addon_name" binding:"required"`
	AddonCategory        string    `json:"addon_category" binding:"required"`
	AddonType            string    `json:"addon_type" binding:"required"`
	AddonVersion         string    `json:"addon_version" binding:"required"`
	RecommendedVersion   string    `json:"recommended_version"`
	SupportedVersions    string    `json:"supported_versions"`
	RecommendedAcVersion string    `json:"recommended_addoncluster_version"`
	SupportedAcVersions  string    `json:"supported_addoncluster_versions"`
	Topologies           string    `json:"topologies"`
	Releases             string    `json:"releases"`
	Description          string    `json:"description" binding:"required"`
	CreatedBy            string    `json:"created_by"`
	CreatedAt            time.Time `json:"created_at"`
	UpdatedBy            string    `json:"updated_by"`
	UpdatedAt            time.Time `json:"updated_at"`
}
