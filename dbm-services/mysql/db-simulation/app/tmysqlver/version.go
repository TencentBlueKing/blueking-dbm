/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package tmysqlver 将业务侧 MySQL 版本字符串映射为 tmysqlparse 可识别的版本号。
package tmysqlver

import "strings"

// Rebuild 将业务版本标签映射为 tmysqlparse --mysql-version 取值。
// 未识别版本回落为空串，由调用方不传 --mysql-version。
func Rebuild(versions []string) (rebuildVers []string) {
	if len(versions) == 0 {
		return
	}
	rebuildVers = make([]string, 0, len(versions))
	for _, bVer := range versions {
		switch {
		case strings.Contains(bVer, "5.5"):
			rebuildVers = append(rebuildVers, "5.5.24")
		case strings.Contains(bVer, "5.6"):
			rebuildVers = append(rebuildVers, "5.6.24")
		case strings.Contains(bVer, "5.7"):
			rebuildVers = append(rebuildVers, "5.7.20")
		case strings.Contains(bVer, "8.0"):
			rebuildVers = append(rebuildVers, "8.0.18")
		case strings.Contains(bVer, "8.4"):
			rebuildVers = append(rebuildVers, "8.4.0")
		default:
			rebuildVers = append(rebuildVers, "")
		}
	}
	return rebuildVers
}
