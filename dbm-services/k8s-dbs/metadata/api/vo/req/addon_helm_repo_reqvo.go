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

import (
	"time"
)

// AddonHelmRepoRespVo addon helm repo req vo 定义
type AddonHelmRepoRespVo struct {
	RepoName       string    `json:"repoName" binding:"required"`
	RepoRepository string    `json:"repoRepository" binding:"required"`
	RepoUsername   string    `json:"repoUsername" binding:"required"`
	RepoPassword   string    `json:"repoPassword" binding:"required"`
	ChartName      string    `json:"chartName" binding:"required"`
	ChartVersion   string    `json:"chartVersion" binding:"required"`
	CreatedBy      string    `json:"createdBy" binding:"required"`
	CreatedAt      time.Time `json:"createdAt"`
	UpdatedBy      string    `json:"updatedBy"`
	UpdatedAt      time.Time `json:"updatedAt"`
}
