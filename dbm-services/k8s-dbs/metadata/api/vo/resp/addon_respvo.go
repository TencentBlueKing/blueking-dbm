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
	ID                 uint64    `json:"id"`
	AddonName          string    `json:"addon_name"`
	AddonCategory      string    `json:"addon_category"`
	AddonType          string    `json:"addon_type"`
	AddonVersion       string    `json:"addon_version"`
	RecommendedVersion string    `json:"recommended_version"`
	SupportedVersions  string    `json:"supported_versions"`
	Topologies         string    `json:"topologies"`
	Releases           string    `json:"releases"`
	Active             bool      `json:"active"`
	Description        string    `json:"description"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
