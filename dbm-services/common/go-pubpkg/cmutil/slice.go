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
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/spf13/cast"
)

// FilterOutStringSlice 滤除scr中含有filters 里面元素的数组
//
//	@receiver src
//	@receiver filters
//	@return dst
func FilterOutStringSlice(src []string, filters []string) (dst []string) {
	for _, v := range src {
		if !StringsHas(filters, v) {
			dst = append(dst, v)
		}
	}
	return
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
	resArr := make([]T, 0)
	tmpMap := make(map[T]struct{})
	for _, val := range arr {
		// 判断主键为val的map是否存在
		if _, ok := tmpMap[val]; !ok {
			resArr = append(resArr, val)
			tmpMap[val] = struct{}{}
		}
	}
	return resArr
}

// IntSliceToStrSlice TODO
func IntSliceToStrSlice(elems []int) (dst []string) {
	for _, v := range elems {
		dst = append(dst, strconv.Itoa(v))
	}
	return dst
}

// IntsJoin join int slice to string
func IntsJoin(intList []int, sep string) string {
	strList := make([]string, len(intList))
	for i, e := range intList {
		strList[i] = cast.ToString(e)
	}
	fmt.Println("intsjoin: ", strList)
	return strings.Join(strList, sep)
}

// SplitGroup 数组切割
// 将数组laxiconid 按照 subGroupLength 切分成若干个数组
func SplitGroup[T int | string](laxiconid []T, subGroupLength int64) [][]T {
	max := int64(len(laxiconid))
	var segmens = make([][]T, 0)
	quantity := max / subGroupLength
	remainder := max % subGroupLength
	if quantity <= 1 {
		segmens = append(segmens, laxiconid)
		return segmens
	}
	i := int64(0)
	for i = int64(0); i < quantity; i++ {
		segmens = append(segmens, laxiconid[i*subGroupLength:(i+1)*subGroupLength])
	}
	if quantity == 0 || remainder != 0 {
		segmens = append(segmens, laxiconid[i*subGroupLength:i*subGroupLength+remainder])
	}
	return segmens
}

// StringsRemoveEmpty TODO
// RemoveEmpty 过滤掉空字符串
func StringsRemoveEmpty(elems []string) []string {
	var result []string
	for _, item := range elems {
		if strings.TrimSpace(item) != "" {
			result = append(result, strings.TrimSpace(item))
		}
	}
	return result
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

// ArrayInGroupsOf TODO
/*
示例1：
数组：[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]，正整数：2
期望结果: [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
调用: res:= arrayInGroupsOf(arr,2)
*/
func ArrayInGroupsOf(arr []string, num int64) [][]string {
	max := int64(len(arr))
	// 判断数组大小是否小于等于指定分割大小的值，是则把原数组放入二维数组返回
	if max <= num {
		return [][]string{arr}
	}
	// 获取应该数组分割为多少份
	var quantity int64
	if max%num == 0 {
		quantity = max / num
	} else {
		quantity = (max / num) + 1
	}
	// 声明分割好的二维数组
	var segments = make([][]string, 0)
	// 声明分割数组的截止下标
	var start, end, i int64
	for i = 1; i <= quantity; i++ {
		end = i * num
		if i != quantity {
			segments = append(segments, arr[start:end])
		} else {
			segments = append(segments, arr[start:])
		}
		start = i * num
	}
	return segments
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
