/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package model

import "time"

// SwitchVersionType 切换版本类型
type SwitchVersionType string

const (
	// SwitchVersionV1 v1版本切换
	SwitchVersionV1 SwitchVersionType = "v1"
	// SwitchVersionV2 v2版本切换
	SwitchVersionV2 SwitchVersionType = "v2"
)

// StatusType 状态类型
type StatusType string

const (
	// StatusEnabled 启用
	StatusEnabled StatusType = "enabled"
	// StatusDisabled 禁用
	StatusDisabled StatusType = "disabled"
)

// HABlackWhiteList 数据库切换黑白名单（v2使用白名单，v1使用黑名单跳过切换）
type HABlackWhiteList struct {
	ID            uint              `gorm:"column:id;primaryKey;autoIncrement" json:"id,omitempty"`
	BkBizID       int               `gorm:"column:bk_biz_id;uniqueIndex:idx_biz_cloud_cluster" json:"bk_biz_id,omitempty"`
	BkCloudID     int               `gorm:"column:bk_cloud_id;uniqueIndex:idx_biz_cloud_cluster" json:"bk_cloud_id,omitempty"`
	ClusterID     int               `gorm:"column:cluster_id;uniqueIndex:idx_biz_cloud_cluster" json:"cluster_id,omitempty"`
	ClusterName   string            `gorm:"column:cluster_name;index:idx_cluster" json:"cluster_name,omitempty"`
	SwitchVersion SwitchVersionType `gorm:"column:switch_version" json:"switch_version,omitempty"`
	Status        StatusType        `gorm:"column:status" json:"status,omitempty"`
	CreatedAt     time.Time         `gorm:"column:created_at;autoCreateTime" json:"created_at,omitempty"`
	UpdatedAt     time.Time         `gorm:"column:updated_at;autoUpdateTime" json:"updated_at,omitempty"`
}

// TableName 返回黑白名单表名
func (t HABlackWhiteList) TableName() string {
	return "t_db_black_white_list"
}
