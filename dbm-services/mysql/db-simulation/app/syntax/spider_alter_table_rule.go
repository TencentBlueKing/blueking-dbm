/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import "fmt"

// SpiderChecker syntax checker
func (c AlterTableResult) SpiderChecker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	for _, altercmd := range c.AlterCommands {
		// 如果是增加字段，需要判断增加的字段名称是否是关键字
		if altercmd.Type == AlterTypeAddColumn {
			r.ParseBultinRisk(func() (bool, string) {
				return KeyWordValidator(mysqlVersion, altercmd.ColDef.ColName)
			})
		}
	}
	r.ParseBultinBan(c.NotAllowedDefaulValCol)
	return
}

// NotAllowedDefaulValCol 不允许存在默认值的字段
func (c AlterTableResult) NotAllowedDefaulValCol() (bool, string) {
	for _, alt := range c.AlterCommands {
		if alt.ColDef.IsNotAllowDefaulValCol() {
			return true, fmt.Sprintf("col:%s,类型:%s 不允许存在默认值的字段", alt.ColDef.ColName, alt.ColDef.DataType)
		}
	}
	return false, ""
}
