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
	"encoding/json"

	corev1 "k8s.io/api/core/v1"
)

// ComponentDetail 组件详情
type ComponentDetail struct {
	Metadata `json:",inline"`
	Pods     []*Pod          `json:"pods,omitempty"`
	Env      []corev1.EnvVar `json:"env,omitempty"`
}

// StorageSize 存储容量大小，单位: GB
type StorageSize int64

// Pod K8s 的 Pod 资源
type Pod struct {
	PodName       string            `json:"podName,omitempty"`
	Role          string            `json:"role,omitempty"`
	Status        corev1.PodPhase   `json:"status,omitempty"`
	Node          string            `json:"node,omitempty"`
	ResourceQuota *PodResourceQuota `json:"resourceQuota,omitempty"`
	ResourceUsage *PodResourceUsage `json:"resourceUsage,omitempty"`
	CreatedTime   string            `json:"createdTime,omitempty"`
}

// PodResourceQuota Pod 资源配额
type PodResourceQuota struct {
	Request *QuotaSummary `json:"request"`
	Limit   *QuotaSummary `json:"limit"`
	Storage *StorageSize  `json:"storage"`
}

// QuotaSummary 配额概要：CPU、Memory以及存储配额
type QuotaSummary struct {
	CPU     *float64     `json:"cpu"`     // 单位: core
	Memory  *float64     `json:"memory"`  // 单位: GB
	Storage *StorageSize `json:"storage"` // 单位: GB
}

// PodResourceUsage Pod 资源利用率
type PodResourceUsage struct {
	*QuotaSummary  `json:",inline"`
	CPUPercent     *float64 `json:"cpuPercent"`     // CPU 利用率（百分比）
	MemoryPercent  *float64 `json:"memoryPercent"`  // 内存利用率（百分比）
	StoragePercent *float64 `json:"storagePercent"` // 存储利用率（百分比）
}

// MarshalJSON 自定义 PodResourceQuota JSON 序列化逻辑
func (p PodResourceQuota) MarshalJSON() ([]byte, error) {
	output := map[string]interface{}{
		"requestCpu":    p.Request.CPU,
		"requestMemory": p.Request.Memory,
		"limitCpu":      p.Limit.CPU,
		"limitMemory":   p.Limit.Memory,
		"storage":       p.Storage,
	}
	return json.Marshal(output)
}
