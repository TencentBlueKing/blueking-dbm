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
	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// Checker TODO
func (c AlterTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	for _, altercmd := range c.AlterCommands {
		r.Parse(R.AlterTableRule.HighRiskType, altercmd.Type, "")
		r.Parse(R.AlterTableRule.HighRiskPkAlterType, altercmd.GetPkAlterType(), "")
		r.Parse(R.AlterTableRule.AlterUseAfter, altercmd.After, "")
		// 如果是增加字段，需要判断增加的字段名称是否是关键字
		if altercmd.Type == ALTER_TYPE_ADD_COLUMN {
			logger.Info("col name is %s", altercmd.ColDef.ColName)
			r.ParseBultinRisk(func() (bool, string) {
				return KeyWordValidator(mysqlVersion, altercmd.ColDef.ColName)
			})
		}
	}
	r.Parse(R.AlterTableRule.AddColumnMixed, c.GetAllAlterType(), "")
	return
}

// GetAllAlterType TODO
// 对于 `alter table add a int(11),drop b,add d int(11);`
// 这种语句，我们需要把 alter type
// 也就是 add,drop,add 提取出来
// 去重后得到所有的alter types
func (c AlterTableResult) GetAllAlterType() (alterTypes []string) {
	for _, a := range c.AlterCommands {
		if !util.StringsHas([]string{"algorithm", "lock"}, a.Type) {
			alterTypes = append(alterTypes, a.Type)
		}
	}
	return util.RemoveDuplicate(alterTypes)
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

// GetAlterAlgorithm TODO
//
//	@receiver a
func (a AlterCommand) GetAlterAlgorithm() string {
	return a.Algorithm
}
