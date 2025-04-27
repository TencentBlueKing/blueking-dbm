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

// K8sClusterServiceEntity cluster service entity 定义
type K8sClusterServiceEntity struct {
	ID            uint64    `json:"id"` // 主键
	CrdClusterID  uint64    `json:"crd_cluster_id"`
	ComponentName string    `json:"component_name"`
	ServiceName   string    `json:"service_name"`
	ServiceType   string    `json:"service_type"`
	Annotations   string    `json:"annotations"`
	InternalAddrs string    `json:"internal_addrs"`
	ExternalAddrs string    `json:"external_addrs"`
	Domains       string    `json:"domains"`
	Description   string    `json:"description"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
