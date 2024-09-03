/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlcomm

import (
	"regexp"
)

var (
	mysqlRegex           = regexp.MustCompile(`(?i)mysql.*-u(\s*)\w+.*\s-p(\S+).*`)
	mysqlAdminRegex      = regexp.MustCompile(`(?i)mysqladmin.*-u\w+.*\s-p(\S+).*`)
	mysqlPasswordRegex   = regexp.MustCompile(`(?i)\s-p\S+`)
	masterPasswordRegexp = regexp.MustCompile(`(?i)master_password="\S+"`)
	// identifyByRegex identified by ''  or IDENTIFIED WITH mysql_native_password BY 'aa'
	identifyByRegex     = regexp.MustCompile(`(?i)identified by '\S+'`)
	identifyWithByRegex = regexp.MustCompile(`(?i)identified (with.*password'? )?by '\S+'`)
	identifyWithAsRegex = regexp.MustCompile(`(?i)identified (with.*password'? )?as '\S+'`)
	userPasswordRegex   = regexp.MustCompile(`(?i)\s-u\S+\s-p(\S+)`)
	dsnRegex            = regexp.MustCompile(`(?i)\w+:\S+@tcp\(\S+\)`)
	dsnPasswordRegex    = regexp.MustCompile(`:\S+@tcp\(`)
	passwordRegex       = regexp.MustCompile(`(?i)password ['"]?\S+['"]?`)
	passwordGrantRegex  = regexp.MustCompile(`(?i)password\(['"]?\S+['"]?\)`)
)

// ClearSensitiveInformation clear sensitive information from input
func ClearSensitiveInformation(input string) string {
	output := RemoveMysqlCommandPassword(input)
	output = ClearMasterPasswordInSQL(output)
	output = RemoveMysqlAdminCommandPassword(output)
	output = clearIdentifyByInSQL(output)
	output = RemovePasswordInDSN(output)
	output = CleanSvrPassword(output)
	output = CleanGrantPassword(output)
	return output
}

// CleanSvrPassword TODO
func CleanSvrPassword(input string) string {
	return passwordRegex.ReplaceAllString(input, "password 'xxxx'")
}

// CleanGrantPassword clean grant sql password
func CleanGrantPassword(input string) string {
	return passwordGrantRegex.ReplaceAllString(input, "password('xxxx')")
}

// clearIdentifyByInSQL TODO
func clearIdentifyByInSQL(input string) string {
	output := identifyByRegex.ReplaceAllString(input, `identified by 'xxxx'`)
	output = identifyWithByRegex.ReplaceAllString(output, "identified ${1}by 'xxxx'")
	output = identifyWithAsRegex.ReplaceAllString(output, "identified ${1}as '*xxxx'")
	return output
}

// ClearIdentifyByInSQLs TODO
func ClearIdentifyByInSQLs(input []string) []string {
	output := make([]string, len(input))
	for i, s := range input {
		s = clearIdentifyByInSQL(s)
		output[i] = CleanGrantPassword(s)
	}
	return output
}

// ClearMasterPasswordInSQL TODO
func ClearMasterPasswordInSQL(input string) string {
	output := masterPasswordRegexp.ReplaceAllString(input, `master_password="xxxx"`)
	return output
}

// RemoveMysqlCommandPassword replace password field
func RemoveMysqlCommandPassword(input string) string {
	return mysqlRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemoveMysqlAdminCommandPassword replace password field
func RemoveMysqlAdminCommandPassword(input string) string {
	return mysqlAdminRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemovePassword replace password in -u -p pattern
func RemovePassword(input string) string {
	return userPasswordRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemovePasswordInDSN TODO
func RemovePasswordInDSN(input string) string {
	return dsnRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return dsnPasswordRegex.ReplaceAllString(sub, `:xxxx@tcp\(`)
	})
}
