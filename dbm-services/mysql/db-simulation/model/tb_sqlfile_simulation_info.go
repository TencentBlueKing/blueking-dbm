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

// TbSqlFileSimulationInfo 记录每个SQL文件模拟执行的结果
type TbSqlFileSimulationInfo struct {
	ID           int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	TaskId       string    `gorm:"uniqueIndex:uk_tk_file,column:task_id;type:varchar(128);not null" json:"task_id"`
	FileNameHash string    `gorm:"uniqueIndex:uk_tk_file,column:file_name_hash;type:varchar(65)" json:"file_name_hash"`
	FileName     string    `gorm:"column:file_name;type:text;not null" json:"file_name"`
	Status       string    `gorm:"column:status;type:varchar(16);not null" json:"status"`
	ErrMsg       string    `gorm:"column:err_msg;type:varchar(512);not null" json:"err_msg"`
	UpdateTime   time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
	CreateTime   time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
}
