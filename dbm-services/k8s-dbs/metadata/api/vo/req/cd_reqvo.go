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

// K8sCrdCdReqVo represents the request data structure of cd meta.
type K8sCrdCdReqVo struct {
	AddonID            uint64    `json:"addonId" binding:"required"`
	CdName             string    `json:"cdName" binding:"required"`
	Topologies         string    `json:"topologies" binding:"required"`
	RecommendedVersion string    `json:"recommendedVersion" binding:"required"`
	Releases           string    `json:"releases" binding:"required"`
	Description        string    `json:"description" binding:"required"`
	CreatedBy          string    `json:"createdBy" binding:"required"`
	CreatedAt          time.Time `json:"createdAt"`
	UpdatedBy          string    `json:"updatedBy"`
	UpdatedAt          time.Time `json:"updatedAt"`
}
