/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil

import (
	"slices"
	"strconv"
	"strings"

	"github.com/samber/lo"
)

// FilterOutStringSlice 滤除scr中含有filters 里面元素的数组
//
//	@receiver src
//	@receiver filters
//	@return dst
func FilterOutStringSlice(src []string, filters []string) (dst []string) {
	return lo.FilterMap(src, func(item string, _ int) (string, bool) {
		return item, !StringsHas(filters, item)
	})
}

// StringsHas check the []string contains the given element
func StringsHas(ss []string, val string) bool {
	return slices.Contains(ss, val)
}

// UniqueInts Returns unique items in a slice
func UniqueInts(slice []int) []int {
	return RemoveDuplicate(slice)
}

// StringsRemove an value form an string slice
func StringsRemove(ss []string, s string) (ns []string) {
	ns = slices.DeleteFunc(ss, func(item string) bool {
		return item == s
	})
	return
}

// RemoveDuplicate 通过map主键唯一的特性过滤重复元素
func RemoveDuplicate[T int | string](arr []T) []T {
	return lo.Uniq(arr)
}

// IntSliceToStrSlice TODO
func IntSliceToStrSlice(elems []int) []string {
	return lo.Map(elems, func(ele int, _ int) string { return strconv.Itoa(ele) })
}

// SplitGroup 数组切割
// 将数组laxiconid 按照 subGroupLength 切分成若干个数组
func SplitGroup[T int | string](laxiconid []T, subGroupLength int) [][]T {
	return lo.Chunk(laxiconid, subGroupLength)
}

// StringsRemoveEmpty TODO
// RemoveEmpty 过滤掉空字符串
func StringsRemoveEmpty(elems []string) []string {
	return lo.Compact(elems)
}

// RemoveEmpty 过滤掉空字符串
func RemoveEmpty(input []string) []string {
	return slices.DeleteFunc(input, func(s string) bool {
		return strings.TrimSpace(s) == ""
	})
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

// ElementNotInArry TODO
func ElementNotInArry(ele string, arry []string) bool {
	if len(arry) <= 0 {
		return true
	}
	for _, v := range arry {
		if strings.TrimSpace(v) == "" {
			continue
		}
		if strings.TrimSpace(v) == ele {
			return false
		}
	}
	return true
}

// HasElem TODO
func HasElem[T int | string](elem T, elems []T) bool {
	if len(elems) <= 0 {
		return true
	}
	for _, v := range elems {
		if elem == v {
			return true
		}
	}
	return false
}

// StringsInsertAfter 在 slice 里插入某个元素之后，仅匹配一次
// 如果没有找到元素，忽略
func StringsInsertAfter(ss []string, old string, new string) []string {
	var ssNew = make([]string, len(ss)+1)
	var found bool
	for i, v := range ss {
		if found {
			ssNew[i+1] = v
		} else if v == old {
			ssNew[i] = v
			ssNew[i+1] = new
			found = true
		} else {
			ssNew[i] = v
		}
	}
	if !found {
		return ssNew[:len(ss)]
	}
	return ssNew
}

// StringsInsertIndex 在 slice index 当前位置，插入一个元素
// 如果 index 非法，则忽略
func StringsInsertIndex(ss []string, index int, new string) []string {
	if index < 0 || index > len(ss)-1 {
		return ss
	}
	var ssNew = make([]string, len(ss)+1)
	for i, v := range ss {
		if i > index {
			ssNew[i+1] = v
		} else if i < index {
			ssNew[i] = v
		} else {
			ssNew[i] = new
			ssNew[i+1] = v
		}
	}
	return ssNew
}
