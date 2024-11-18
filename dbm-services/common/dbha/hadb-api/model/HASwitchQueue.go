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

// HASwitchQueue TODO
type HASwitchQueue struct {
	Uid                int64      `gorm:"column:uid;type:bigint;primary_key;AUTO_INCREMENT" json:"uid,omitempty"`
	CheckID            int64      `gorm:"column:check_id;type:bigint;" json:"check_id,omitempty"`
	App                string     `gorm:"column:app;type:varchar(32);index:idx_app_ip_port" json:"app,omitempty"`
	IP                 string     `gorm:"column:ip;type:varchar(32);index:idx_app_ip_port;NOT NULL" json:"ip,omitempty"`
	Port               int        `gorm:"column:port;type:int(11);index:idx_app_ip_port;NOT NULL" json:"port,omitempty"`
	ConfirmCheckTime   *time.Time `gorm:"column:confirm_check_time;type:datetime;default:CURRENT_TIMESTAMP" json:"confirm_check_time,omitempty"`
	DbRole             string     `gorm:"column:db_role;type:varchar(32);NOT NULL" json:"db_role,omitempty"`
	SlaveIP            string     `gorm:"column:slave_ip;type:varchar(32)" json:"slave_ip,omitempty"`
	SlavePort          int        `gorm:"column:slave_port;type:int(11)" json:"slave_port,omitempty"`
	Status             string     `gorm:"column:status;type:varchar(32);" json:"status,omitempty"`
	ConfirmResult      string     `gorm:"column:confirm_result;type:blob" json:"confirm_result,omitempty"`
	SwitchStartTime    *time.Time `gorm:"column:switch_start_time;type:datetime" json:"switch_start_time,omitempty"`
	SwitchFinishedTime *time.Time `gorm:"column:switch_finished_time;type:datetime" json:"switch_finished_time,omitempty"`
	SwitchResult       string     `gorm:"column:switch_result;type:blob" json:"switch_result,omitempty"`
	Remark             string     `gorm:"column:remark;type:varchar(64)" json:"remark,omitempty"`
	DbType             string     `gorm:"column:db_type;type:varchar(32)" json:"db_type,omitempty"`
	IdcID              int        `gorm:"column:idc_id;type:int(11)" json:"idc_id,omitempty"`
	CloudID            int        `gorm:"column:cloud_id;type:int(11);default:0" json:"cloud_id,omitempty"`
	Cluster            string     `gorm:"column:cluster;type:varchar(64)" json:"cluster,omitempty"`
}

// TableName TODO
func (m *HASwitchQueue) TableName() string {
	return "ha_switch_queue"
}
