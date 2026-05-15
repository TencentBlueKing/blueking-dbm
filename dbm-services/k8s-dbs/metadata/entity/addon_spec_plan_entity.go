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

import commtypes "k8s-dbs/common/types"

// AddonSpecPlanEntity 存储套餐配置实体定义
type AddonSpecPlanEntity struct {
	ID             uint64                 `json:"id"`
	AddonID        uint64                 `json:"addonId"`
	AddonTopology  string                 `json:"addonTopology"`
	SpecLevel      string                 `json:"specLevel"`
	SpecLevelAlias string                 `json:"specLevelAlias"`
	Active         bool                   `json:"active"`
	Description    string                 `json:"description"`
	CreatedBy      string                 `json:"createdBy"`
	CreatedAt      commtypes.JSONDatetime `json:"createdAt"`
	UpdatedBy      string                 `json:"updatedBy"`
	UpdatedAt      commtypes.JSONDatetime `json:"updatedAt"`
}

// AddonSpecPlanDetailQueryParams 套餐详情聚合查询参数
type AddonSpecPlanDetailQueryParams struct {
	AddonType     string `json:"addonType"`
	AddonVersion  string `json:"addonVersion"`
	AddonTopology string `json:"addonTopology"`
}

// ComponentSpecBriefEntity 套餐组件简要信息（用于聚合返回）
type ComponentSpecBriefEntity struct {
	ID            uint64 `json:"id"`
	ComponentName string `json:"componentName"`
	CPUCores      *int   `json:"cpuCores"`
	MemoryGb      *int   `json:"memoryGb"`
	DiskSizeGb    *int   `json:"diskSizeGb"`
}

// AddonSpecPlanDetailEntity addon 套餐配置（含组件）的聚合实体
type AddonSpecPlanDetailEntity struct {
	ID             uint64                     `json:"id"`
	AddonType      string                     `json:"addonType"`
	AddonVersion   string                     `json:"addonVersion"`
	AddonTopology  string                     `json:"addonTopology"`
	DbmClusterType string                     `json:"dbmClusterType"`
	SpecLevel      string                     `json:"specLevel"`
	SpecLevelAlias string                     `json:"specLevelAlias"`
	Components     []ComponentSpecBriefEntity `json:"components"`
}
