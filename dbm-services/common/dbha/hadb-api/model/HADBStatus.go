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

import (
	"time"
)

// HADbStatus TODO
type HADbStatus struct {
	Uid      uint       `gorm:"column:uid;type:bigint;primary_key;AUTO_INCREMENT" json:"uid,omitempty"`
	AgentIP  string     `gorm:"column:agent_ip;index:idx_ins;type:varchar(32);NOT NULL" json:"agent_ip,omitempty"`
	IP       string     `gorm:"column:ip;index:idx_ins;type:varchar(32);NOT NULL" json:"ip,omitempty"`
	Port     int        `gorm:"column:port;index:idx_ins;type:int(11);NOT NULL" json:"port,omitempty"`
	DbType   string     `gorm:"column:db_type;type:varchar(32);NOT NULL" json:"db_type,omitempty"`
	Status   string     `gorm:"column:status;type:varchar(32);NOT NULL" json:"status,omitempty"`
	CloudID  int        `gorm:"column:cloud_id;type:int(11);NOT NULL;default:0" json:"cloud_id,omitempty"`
	LastTime *time.Time `gorm:"column:last_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL" json:"last_time,omitempty"`
}

// TableName TODO
func (m *HADbStatus) TableName() string {
	return "ha_db_status"
}
