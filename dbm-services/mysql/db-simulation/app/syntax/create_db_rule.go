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

// Checker create db syntax checker
func (c CreateDBResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	// 检查库名规范
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		r.ParseBultinRisk(func() (bool, string) {
			return KeyWordValidator(mysqlVersion, c.DbName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpeicalChar {
		r.ParseBultinBan(func() (bool, string) {
			return SpecialCharValidator(c.DbName)
		})
	}
	return
}

// SpiderChecker spider create db syntax checker
func (c CreateDBResult) SpiderChecker(mysqlVersion string) (r *CheckerResult) {
	return c.Checker(mysqlVersion)
}
