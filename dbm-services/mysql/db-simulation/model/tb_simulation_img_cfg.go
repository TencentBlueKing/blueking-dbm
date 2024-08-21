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

// TbSimulationImgCfg 模拟执行镜像配置表
type TbSimulationImgCfg struct {
	ID            int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	ComponentType string    `gorm:"unique;column:component_type;type:varchar(64);not null" json:"component_type"`
	Version       string    `gorm:"unique;column:version;type:varchar(64);not null" json:"version"`
	Image         string    `gorm:"column:image;type:varchar(128);not null" json:"image"`
	UpdateTime    time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
	CreateTime    time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
}

// GetImageName 获取镜像名称
func GetImageName(componentType, version string) (image string, err error) {
	err = DB.Model(&TbSimulationImgCfg{}).Select("image").Where("component_type = ? AND version = ?", componentType,
		version).
		First(&image).Error
	return
}
