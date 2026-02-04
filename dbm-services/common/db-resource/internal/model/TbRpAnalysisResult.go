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
	"encoding/json"
	"time"
)

const (
	// AnalysisStatusPending 待分析
	AnalysisStatusPending = "pending"
	// AnalysisStatusRunning 分析中
	AnalysisStatusRunning = "running"
	// AnalysisStatusCompleted 已完成
	AnalysisStatusCompleted = "completed"
	// AnalysisStatusFailed 失败
	AnalysisStatusFailed = "failed"
)

// TbRpAnalysisResult 资源申请智能分析结果表
type TbRpAnalysisResult struct {
	ID             int             `gorm:"primaryKey;auto_increment;not null" json:"id"`
	BillId         string          `gorm:"uniqueIndex:uk_bill_id;column:bill_id;type:varchar(128);not null" json:"bill_id"`
	ApplyParams    json.RawMessage `gorm:"column:apply_params;type:json;not null" json:"apply_params"`
	AnalysisResult json.RawMessage `gorm:"column:analysis_result;type:json" json:"analysis_result"`
	MarkdownText   string          `gorm:"column:markdown_text;type:text" json:"markdown_text"`
	Status         string          `gorm:"index:idx_status;column:status;type:varchar(20);not null;default:'pending'" json:"status"`
	ErrorMsg       string          `gorm:"column:error_msg;type:text" json:"error_msg"`
	Duration       string          `gorm:"column:duration;type:varchar(32)" json:"duration"`
	CreateTime     time.Time       `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP" json:"create_time"`
	UpdateTime     time.Time       `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP" json:"update_time"`
}

// TableName 表名
func (TbRpAnalysisResult) TableName() string {
	return "tb_rp_analysis_result"
}
