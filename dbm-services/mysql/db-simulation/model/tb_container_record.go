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

	"dbm-services/common/go-pubpkg/logger"
)

// TbContainerRecord TODO
type TbContainerRecord struct {
	ID            int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	Uid           string    `gorm:"column:uid;type:varchar(255);not null" json:"uid"`
	Container     string    `gorm:"column:container;type:varchar(255);not null" json:"container"`
	CreatePodTime time.Time `gorm:"column:create_pod_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_pod_time"`
	PodReadyTime  time.Time `gorm:"column:pod_ready_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"pod_ready_time"`
	UpdateTime    time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
	CreateTime    time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
}

// GetTableName get sql table name.获取数据库名字
func (obj *TbContainerRecord) GetTableName() string {
	return "tb_container_record"
}

// UpdateTbContainerRecord TODO
func UpdateTbContainerRecord(container string) {
	err := DB.Model(TbContainerRecord{}).Where("container = ?", container).Updates(
		TbContainerRecord{
			PodReadyTime: time.Now(),
			UpdateTime:   time.Now(),
		}).Error
	if err != nil {
		logger.Error("update heartbeat time failed %s", err.Error())
	}
}

// CreateTbContainerRecord TODO
func CreateTbContainerRecord(m *TbContainerRecord) {
	DB.Create(m)
}
