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
	"log/slog"

	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var CustimazationMap map[int64]string

// Custimazation TODO
type Custimazation struct {
	id              int    `gorm:"column:id"`
	BkBizId         int64  `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	PartitionColumn string `json:"partition_column" gorm:"column:partition_column"`
	ImmuteDomain    string `json:"immute_domain" gorm:"column:immute_domain"`
}

func InitCustimazation() {
	CustimazationMap = make(map[int64]string)
	custimazations := []Custimazation{}
	result := DB.Self.Session(&gorm.Session{
		Logger: logger.Default.LogMode(logger.Info),
	}).Table("partition_customization_config").Find(&custimazations)
	if result.Error != nil {
		slog.Error("定制化配置读取失败！", result.Error)
	}
	for _, cs := range custimazations {
		if cs.ImmuteDomain != "" {
			CustimazationMap[cs.BkBizId] = cs.ImmuteDomain
		} else if cs.PartitionColumn != "" {
			CustimazationMap[cs.BkBizId] = cs.PartitionColumn
		}
	}
}
