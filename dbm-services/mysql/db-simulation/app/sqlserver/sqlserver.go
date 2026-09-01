/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package sqlserver SQLServer syntax check module.
// 当前阶段仅提供文件编码前置检查（UTF-8 BOM），后续会在此包下扩展 T-SQL 语法解析、规则校验等能力。
package sqlserver

// FileCheckStatus 单个文件检查的状态
type FileCheckStatus string

const (
	// FileCheckPass 通过
	FileCheckPass FileCheckStatus = "pass"
	// FileCheckFail 未通过
	FileCheckFail FileCheckStatus = "fail"
)

// FileCheckResult 单个文件的检查结果
// 说明：该结构是 SQLServer 语法检查模块对外统一的最小结果单元，
// 后续追加 parser / rule 检查时，会在此基础上扩展字段（如 SyntaxFailInfos、RiskWarnings 等）。
type FileCheckResult struct {
	// FileName 文件名
	FileName string `json:"file_name"`
	// Status 检查状态：pass / fail
	Status FileCheckStatus `json:"status"`
	// Encoding 实际探测到的编码类型（utf-8-bom / utf-8 / utf-16-le-bom / utf-16-be-bom / unknown）
	Encoding string `json:"encoding"`
	// Message 说明信息（不通过时给出具体原因）
	Message string `json:"message,omitempty"`
}
