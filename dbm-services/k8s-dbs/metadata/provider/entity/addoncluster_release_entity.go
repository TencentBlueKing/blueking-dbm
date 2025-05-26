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
	"time"
)

// AddonClusterReleaseEntity addon cluster release 定义
type AddonClusterReleaseEntity struct {
	ID                 uint64    `json:"id"`
	RepoName           string    `json:"repo_name"`
	RepoRepository     string    `json:"repo_repository"`
	ChartVersion       string    `json:"chart_version"`
	ChartName          string    `json:"chart_name"`
	Namespace          string    `json:"namespace"`
	K8sClusterConfigID uint64    `json:"k8s_cluster_config_id"`
	ReleaseName        string    `json:"release_name"`
	ChartValues        string    `json:"chart_values"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
