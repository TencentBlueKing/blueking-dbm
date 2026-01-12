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

// AddonParamConfigModel 组件参数配置模型
// 用于存储各存储类型组件支持的参数配置
type AddonParamConfigModel struct {
	ID             uint64                 `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	AddonID        uint64                 `gorm:"not null;column:addon_id" json:"addonId"`
	ServiceVersion string                 `gorm:"size:32;not null;column:service_version" json:"serviceVersion"`
	ComponentName  string                 `gorm:"size:32;not null;column:component_name" json:"componentName"`
	ParamName      string                 `gorm:"size:64;not null;column:param_name" json:"paramName"`
	ParamType      string                 `gorm:"size:32;not null;column:param_type" json:"paramType"`
	DefaultValue   *string                `gorm:"size:64;column:default_value" json:"defaultValue"`
	Active         bool                   `gorm:"type:tinyint(1);not null;default:1;column:active" json:"active"`
	CreatedBy      string                 `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt      commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy      string                 `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt      commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// TableName 获取 model 对应的数据库表名
func (AddonParamConfigModel) TableName() string {
	return constant.TbAddonParamsConfig
}
