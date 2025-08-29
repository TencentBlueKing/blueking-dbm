/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"fmt"
	"slices"
	"sort"
	"strconv"
	"strings"

	"github.com/samber/lo"
)

// ContainElem 判断val 是否在elems 中
func ContainElem[T int | int64 | string](elems []T, val T) bool {
	return slices.Contains(elems, val)
}

// StringsHas check the []string contains the given element
func StringsHas(ss []string, val string) bool {
	return slices.Contains(ss, val)
}

// StringsHasICase check the []string contains the given element. insensitive case
func StringsHasICase(ss []string, val string) bool {
	val = strings.ToLower(val)
	for _, ele := range ss {
		if strings.ToLower(ele) == val {
			return true
		}
	}
	return false
}

// UniqueSlice TODO
func UniqueSlice[T string | int](slice []T) []T {
	uniqMap := make(map[T]struct{})
	for _, v := range slice {
		uniqMap[v] = struct{}{}
	}

	// turn the map keys into a slice
	uniqSlice := make([]T, 0, len(uniqMap))
	for v := range uniqMap {
		uniqSlice = append(uniqSlice, v)
	}
	return uniqSlice
}

// UniqueStrings Returns unique items in a slice
func UniqueStrings(slice []string) []string {
	return lo.Uniq(slice)
	//return UniqueSlice(slice)
}

// UniqueInts Returns unique items in a slice
func UniqueInts(slice []int) []int {
	return lo.Uniq(slice)
	//return UniqueSlice(slice)
}

// IsConsecutiveStrings 是否是连续数字
// 如果存在 空元素 则报错
// 如果 isNumber=false, 则当做字符比较是否连续
func IsConsecutiveStrings(strList []string, isNumber bool) ([]int, error) {
	intList := make([]int, len(strList))
	if !isNumber {
		// string to ascii
		// .aa .ab .ac => 469797 469798 469799
		for i, s := range strList {
			ss := ""
			for _, si := range []rune(s) {
				ss += strconv.FormatInt(int64(si), 10)
			}
			// todo ss 不能超过20位
			strList[i] = ss
		}
	}
	for i, s := range strList {
		if d, e := strconv.Atoi(s); e != nil {
			return nil, fmt.Errorf("illegal number %s", s)
		} else {
			intList[i] = d
		}
	}
	ok, leakInts := CheckConsecutiveInts(intList)
	if !ok {
		return leakInts, fmt.Errorf("not consecutive numbers")
	}
	return nil, nil
}

// CheckConsecutiveInts 检查整数切片是否连续，并返回缺失的整数（如果有）
func CheckConsecutiveInts(intList []int) (bool, []int) {
	if len(intList) <= 1 {
		return true, nil
	}
	intList = lo.Uniq(intList)
	sort.Ints(intList)
	if intList[len(intList)-1]-intList[0]+1 == len(intList) {
		return true, nil
	}
	var targetList []int
	for i := intList[0]; i <= intList[len(intList)-1]; i++ {
		targetList = append(targetList, i)
	}
	leakInts, _ := lo.Difference(targetList, intList)
	return false, leakInts
}

// StringSliceToInterfaceSlice 把字符串数组转换为interface{}数组
func StringSliceToInterfaceSlice(ids []string) []interface{} {
	var result []interface{}
	if len(ids) == 1 {
		result = append(result, ids[0])
	} else {
		for i := 0; i < len(ids); i++ {
			result = append(result, ids[i])
		}
	}
	return result
}

// FilterOutStringSlice 滤除scr中含有filters 里面元素的数组
//
//	@receiver src
//	@receiver filters
//	@return dst
func FilterOutStringSlice(src []string, filters []string) (dst []string) {
	for _, v := range src {
		if !ContainElem(filters, v) {
			dst = append(dst, v)
		}
	}
	return
}

// RemoveNilElements TODO
func RemoveNilElements(v []interface{}) []interface{} {
	newSlice := make([]interface{}, 0, len(v))
	for _, i := range v {
		if i != nil {
			newSlice = append(newSlice, i)
		}
	}
	return newSlice
}
