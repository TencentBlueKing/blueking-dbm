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

package model

import (
	commtypes "k8s-dbs/common/types"
	"k8s-dbs/metadata/constant"
)

// AuthUserRoleModel 用户角色授权表
type AuthUserRoleModel struct {
	ID          uint64                 `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	UserID      string                 `gorm:"size:64;not null;column:user_id" json:"userId"`
	RoleID      string                 `gorm:"size:64;not null;column:role_id" json:"roleId"`
	ScopeID     string                 `gorm:"size:128;not null;column:scope_id" json:"scopeId"`
	AuthStatus  string                 `gorm:"size:32;not null;column:auth_status" json:"authStatus"`
	ExpiredDate commtypes.JSONDatetime `gorm:"type:timestamp;column:expired_date" json:"expiredDate"`
	CreatedBy   string                 `gorm:"size:64;not null;column:created_by" json:"createdBy"`
	CreatedAt   commtypes.JSONDatetime `gorm:"timestamp;not null;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy   string                 `gorm:"size:64;column:updated_by" json:"updatedBy"`
	UpdatedAt   commtypes.JSONDatetime `gorm:"timestamp;column:updated_at" json:"updatedAt"`
	Description string                 `gorm:"size:256;column:description" json:"description"`
}

// TableName 获取表名
func (AuthUserRoleModel) TableName() string {
	return constant.TbAuthUserRole
}
