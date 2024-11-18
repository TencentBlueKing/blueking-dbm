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

// HASwitchLogs TODO
type HASwitchLogs struct {
	UID      int64      `gorm:"column:uid;type:bigint;primaryKey;autoIncrement" json:"uid,omitempty"`
	SwitchID int64      `gorm:"column:sw_id;type:bigint;index:idx_sw_id" json:"sw_id,omitempty"`
	App      string     `gorm:"column:app;type:varchar(32);NOT NULL" json:"app,omitempty"`
	IP       string     `gorm:"column:ip;type:varchar(32);index:idx_ip_port" json:"ip,omitempty"`
	Port     int        `gorm:"column:port;type:int(11);index:idx_ip_port" json:"port,omitempty"`
	Result   string     `gorm:"column:result;type:blob" json:"result,omitempty"`
	Datetime *time.Time `gorm:"column:datetime;type:datetime;index:idx_date" json:"datetime,omitempty"`
	Comment  string     `gorm:"column:comment;type:tinyblob" json:"comment,omitempty"`
}

// TableName TODO
func (s *HASwitchLogs) TableName() string {
	return "ha_switch_logs"
}
