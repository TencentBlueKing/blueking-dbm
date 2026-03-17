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

package response

import "encoding/json"

// PermissionAction 权限申请数据中的操作详情
type PermissionAction struct {
	ID                   string                `json:"id"`
	Name                 string                `json:"name"`
	RelatedResourceTypes []RelatedResourceType `json:"related_resource_types"`
}

// RelatedResourceType 操作关联的资源类型
type RelatedResourceType struct {
	SystemID   string               `json:"system_id"`
	SystemName string               `json:"system_name"`
	Type       string               `json:"type"`
	TypeName   string               `json:"type_name"`
	Instances  [][]ResourceInstance `json:"instances"`
}

// ResourceInstance 资源实例
type ResourceInstance struct {
	Type     string `json:"type"`
	TypeName string `json:"type_name"`
	ID       string `json:"id"`
	Name     string `json:"name"`
}

// PermissionData 权限申请数据
type PermissionData struct {
	SystemID   string             `json:"system_id"`
	SystemName string             `json:"system_name"`
	Actions    []PermissionAction `json:"actions"`
}

// ApplyData 无权限时返回的完整申请数据（permission + apply_url）
type ApplyData struct {
	Permission PermissionData `json:"permission"`
	ApplyURL   string         `json:"apply_url"`
}

// SimpleCheckAllowedResponse 对应 DBM /iam/simple_check_allowed/ 的响应
// Data 字段类型不固定：
//   - 有权限时：code=0, data=true（bool）
//   - 无权限且 is_raise_exception=true 时：code=9900403, data={permission, apply_url}（ApplyData）
type SimpleCheckAllowedResponse struct {
	Result  bool            `json:"result"`
	Code    int             `json:"code"`
	Data    json.RawMessage `json:"data"`
	Message string          `json:"message"`
}

// PermissionDeniedCode DBM 权限不足错误码
const PermissionDeniedCode = 9900403
