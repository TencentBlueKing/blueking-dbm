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
	"k8s-dbs/metadata/constant"
	"time"
)

// ClusterRequestRecordModel represents the database model of request record
type ClusterRequestRecordModel struct {
	ID            uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	RequestID     string    `gorm:"size:50;not null;column:request_id" json:"request_id"`
	RequestType   string    `gorm:"size:50;not null;column:request_type" json:"request_type"`
	RequestParams string    `gorm:"type:text;column:request_params" json:"request_params"`
	Status        string    `gorm:"size:32;column:status" json:"status"`
	Description   string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy     string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"` //nolint:lll
	UpdatedBy     string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"` //nolint:lll
}

// TableName 获取 model 对应的数据库表名
func (ClusterRequestRecordModel) TableName() string {
	return constant.TbClusterRequestRecord
}
