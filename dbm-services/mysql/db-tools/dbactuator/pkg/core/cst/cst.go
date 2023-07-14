/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package cst 常量
package cst

import "time"

const (
	// Environment TODO
	Environment = "enviroment"
	// Test TODO
	Test = "test"
)

const (
	// TIMELAYOUT TODO
	TIMELAYOUT = "2006-01-02 15:04:05"
	// TIMELAYOUTSEQ TODO
	TIMELAYOUTSEQ = "2006-01-02_15:04:05"
	// TimeLayoutDir TODO
	TimeLayoutDir = "20060102150405"
)

const (
	// BK_PKG_INSTALL_PATH 默认文件下发路径
	BK_PKG_INSTALL_PATH = "/data/install"
	// MYSQL_TOOL_INSTALL_PATH 默认工具安装路径
	MYSQL_TOOL_INSTALL_PATH = "/home/mysql"
)

// GetNowTimeLayoutStr 20060102150405
func GetNowTimeLayoutStr() string {
	return time.Now().Format(TimeLayoutDir)
}
