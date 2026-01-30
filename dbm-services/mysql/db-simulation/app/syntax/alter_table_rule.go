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

import (
	"fmt"

	"github.com/samber/lo"
)

// Checker syntax checker
func (c AlterTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{
		ObjName: c.TableName,
	}
	for _, alterCmd := range c.AlterCommands {
		r.Parse(R.AlterTableRule.HighRiskType, alterCmd.Type, "")
		r.Parse(R.AlterTableRule.HighRiskPkAlterType, alterCmd.GetPkAlterType(), "")
		r.Parse(R.AlterTableRule.AlterUseAfter, alterCmd.After, "")
		// 如果是增加字段，需要判断增加的字段名称是否是关键字
		if alterCmd.Type == AlterTypeAddColumn {
			r.ParseBuiltinRisk(func() (bool, string) {
				return KeyWordValidator(mysqlVersion, alterCmd.ColDef.ColName)
			})
		}
	}
	r.Parse(R.AlterTableRule.AddColumnMixed, c.GetAllAlterType(), "")
	r.ParseBuiltinBan(c.JsonColumInvalidDefaultCheck)
	return
}

// GetAllAlterType get all alter types
// 对于 `alter table add a int(11),drop b,add d int(11);`
// 这种语句，我们需要把 alter type
// 也就是 add,drop,add 提取出来
// 去重后得到所有的alter types
func (c AlterTableResult) GetAllAlterType() (alterTypes []string) {
	for _, a := range c.AlterCommands {
		if !lo.Contains([]string{"algorithm", "lock"}, a.Type) {
			alterTypes = append(alterTypes, a.Type)
		}
	}
	return lo.Uniq(alterTypes)
}

// GetPkAlterType  get the primary key change type
//
//	@receiver a
func (a AlterCommand) GetPkAlterType() string {
	if a.ColDef.PrimaryKey {
		return a.Type
	}
	return ""
}

// GetAlterAlgorithm get the alter algorithm
//
//	@receiver a
func (a AlterCommand) GetAlterAlgorithm() string {
	return a.Algorithm
}

// JsonColumInvalidDefaultCheck 检查json列的默认值是否无效
func (c AlterTableResult) JsonColumInvalidDefaultCheck() (bool, string) {
	for _, alterCmd := range c.AlterCommands {
		if alterCmd.ColDef.DataType == JsonDataType {
			if alterCmd.ColDef.HasInvalidJsonDefault() {
				return true, fmt.Sprintf("json 列 %s 的默认值无效，不允许为 '' 或 'null'", alterCmd.ColDef.ColName)
			}
		}
	}
	return false, ""
}
