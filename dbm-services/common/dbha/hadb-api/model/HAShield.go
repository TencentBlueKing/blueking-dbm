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

type ShieldStrategy string

const (
	//ShieldSwitch shield switch
	ShieldSwitch ShieldStrategy = "shield_detect"
	//ShieldCheck shield checksum/slave delay
	ShieldCheck ShieldStrategy = "shield_check"
)

// HAShield struct for ha_shield_config table
type HAShield struct {
	Uid              uint       `gorm:"column:uid;primary_key;AUTO_INCREMENT" json:"uid,omitempty"`
	APP              string     `gorm:"column:app;type:varchar(30);NOT NULL" json:"app,omitempty"`
	Ip               string     `gorm:"column:ip;type:varchar(30);NOT NULL" json:"ip,omitempty"`
	IgnoreCheckSum   bool       `gorm:"column:ignore_checksum;type:tinyint" json:"ignore_checksum,omitempty"`
	IgnoreSlaveDelay bool       `gorm:"column:ignore_slave_delay;type:tinyint" json:"ignore_slave_delay,omitempty"`
	StartTime        *time.Time `gorm:"column:start_time;type:datetime;default:CURRENT_TIMESTAMP" json:"start_time,omitempty"`
	EndTime          *time.Time `gorm:"column:end_time;type:datetime;default:CURRENT_TIMESTAMP" json:"end_time,omitempty"`
	ShieldType       string     `gorm:"column:shield_type;NOT NULL;type:enum('shield_detect','shield_check')" json:"shield_type,omitempty"`
}

// TableName table name
func (m *HAShield) TableName() string {
	return "ha_shield_config"
}
