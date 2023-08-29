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
	"regexp"

	"dbm-services/mysql/db-simulation/app/keyworld"
)

const (

	// SpecialCharRegex = `[￥$!@#%^&*()+={}\[\];:'"<>,.?/\\| ]`

	// AllowWordRegex TODO
	AllowWordRegex = `^[a-zA-Z0-9][a-zA-Z0-9_-]+[a-zA-Z0-9]$`
	// SysReservesPrefixName TODO

)

var reAllowWord *regexp.Regexp

// var mysql55WordMap  map[string]struct{}
var mysql56WordMap map[string]struct{}
var mysql57WordMap map[string]struct{}
var mysql80WordMap map[string]struct{}
var defaultWordMap map[string]struct{}
var sysReservesPrefixNames []string

func init() {
	sysReservesPrefixNames = []string{"stage_truncate"}
	reAllowWord = regexp.MustCompile(AllowWordRegex)
	mysql56WordMap = sliceToMap(keyworld.MySQL56_KEYWORD)
	mysql57WordMap = sliceToMap(keyworld.MySQL57_KEYWORD)
	mysql80WordMap = sliceToMap(keyworld.MySQL80_KEYWORD)
	defaultWordMap = sliceToMap(keyworld.ALL_KEYWORD)
}

// KeyWordValidator TODO
func KeyWordValidator(ver, name string) (matched bool, msg string) {
	var kwmap map[string]struct{}
	switch ver {
	case "mysql5.6":
		kwmap = mysql56WordMap
	case "mysql5.7":
		kwmap = mysql57WordMap
	case "mysql8.0":
		kwmap = mysql80WordMap
	default:
		kwmap = defaultWordMap
	}
	if existInKeywords(name, kwmap) {
		return true, name + " is  mysql keyword"
	}
	return
}

// SpecialCharValidator TODO
func SpecialCharValidator(name string) (matched bool, msg string) {
	if !reAllowWord.MatchString(name) {
		return true, "Only allowed  " + AllowWordRegex + " characters "
	}
	for _, sysPrefix := range sysReservesPrefixNames {
		re := regexp.MustCompile(fmt.Sprintf("^%s", sysPrefix))
		if re.MatchString(name) {
			return true, "不允许以" + sysPrefix + "开头的关键字,前缀被系统占用"
		}
	}
	return
}

func existInKeywords(name string, keywordsmap map[string]struct{}) bool {
	_, ok := keywordsmap[name]
	return ok
}

func sliceToMap(elems []string) map[string]struct{} {
	m := make(map[string]struct{})
	for _, elem := range elems {
		m[elem] = struct{}{}
	}
	return m
}
