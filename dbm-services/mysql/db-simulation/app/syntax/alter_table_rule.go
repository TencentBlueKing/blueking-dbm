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
		objDesc := alterCmd.RiskObjectDesc()
		// HighRiskTypeVal：多数用解析 type；CONVERT TO 派生为 convert_charset（避免 table_options 整类误伤）
		// ExtraMessageKey：drop_primary / convert_charset 等专属文案 key
		r.ParseWithExtraKey(
			R.AlterTableRule.HighRiskType,
			alterCmd.HighRiskTypeVal(),
			alterCmd.ExtraMessageKey(),
			objDesc,
		)
		r.Parse(R.AlterTableRule.HighRiskPkAlterType, alterCmd.GetPkAlterType(), objDesc)
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

// HighRiskTypeVal 返回 HighRiskType 规则匹配用的 Val
// CONVERT TO CHARACTER SET 的解析 type 是 table_options，仅 convert 派生为 convert_charset 进入 item
func (a AlterCommand) HighRiskTypeVal() string {
	if a.Type == AlterTypeTableOptions && a.Action == AlterActionConvert {
		return HighRiskConvertCharset
	}
	return a.Type
}

// ExtraMessageKey 返回 ExtraMessageMap 查找 key
// - DROP PRIMARY KEY：type 仍是 drop_key，文案 key 用 drop_primary
// - CONVERT TO CHARACTER SET：文案 key 用 convert_charset
func (a AlterCommand) ExtraMessageKey() string {
	if a.Type == AlterTypeDropKey && a.DropPrimary {
		return "drop_primary"
	}
	if a.Type == AlterTypeTableOptions && a.Action == AlterActionConvert {
		return HighRiskConvertCharset
	}
	return a.Type
}

// RiskObjectDesc 返回高危变更对应的对象描述（字段/索引/表名），无则返回空串
func (a AlterCommand) RiskObjectDesc() string {
	switch a.Type {
	case AlterTypeAddColumn, AlterTypeDropColumn, "change_column", "modify_column":
		if a.ColDef.ColName != "" {
			return fmt.Sprintf("字段: %s", a.ColDef.ColName)
		}
	case "add_key", AlterTypeDropKey, "rename_key":
		if a.Type == AlterTypeDropKey && a.DropPrimary {
			return "主键"
		}
		if a.Type == "rename_key" && (a.OldKeyName != "" || a.NewKeyName != "") {
			return fmt.Sprintf("索引: %s→%s", a.OldKeyName, a.NewKeyName)
		}
		if a.KeyDef.KeyName != "" {
			return fmt.Sprintf("索引: %s", a.KeyDef.KeyName)
		}
		if a.OldKeyName != "" {
			return fmt.Sprintf("索引: %s", a.OldKeyName)
		}
	case AlterTypeTableOptions:
		if a.Action == AlterActionConvert {
			return "字符集转换"
		}
	case "rename_table":
		if a.TableName != "" {
			return fmt.Sprintf("表: %s", a.TableName)
		}
	}
	return ""
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
