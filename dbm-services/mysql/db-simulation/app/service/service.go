/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package service service
package service

// SpiderSimulationExecParam tendbcluster request param
type SpiderSimulationExecParam struct {
	BaseParam
	SpiderVersion string `json:"spider_version"`
}

// ExcuteSQLFileObj execution object of a single file
type ExcuteSQLFileObj struct {
	LineID        int      `json:"line_id"`
	SQLFile       string   `json:"sql_file"  binding:"required"` // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"`               // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"  binding:"gt=0"`      // 需要变更的DBNames,支持模糊匹配
}

// ExcuteSQLFileObjV2 support for multiple file changes
type ExcuteSQLFileObjV2 struct {
	LineID        int      `json:"line_id"`
	SQLFiles      []string `json:"sql_files"  binding:"required,gt=0"` // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"`                     // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"  binding:"gt=0"`            // 需要变更的DBNames,支持模糊匹配
}
