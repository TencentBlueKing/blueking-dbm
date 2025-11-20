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

// OperationDefinitionModel represents the database model of operation definition
type OperationDefinitionModel struct {
	ID              uint64                 `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	OperationName   string                 `gorm:"size:32;not null;column:operation_name" json:"operationName"`
	OperationTarget string                 `gorm:"size:32;not null;column:operation_target" json:"operationTarget"`
	Active          bool                   `gorm:"type:tinyint(1);not null;default:1;column:active" json:"active"`
	Description     string                 `gorm:"size:100;column:description" json:"description"`
	CreatedBy       string                 `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt       commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy       string                 `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt       commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// TableName 获取 model 对应的数据库表名
func (OperationDefinitionModel) TableName() string {
	return constant.TbOperationDefinition
}
