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
	for _, ele := range ss {
		if ele == val {
			return true
		}
	}
	return false
}

// UniqueInts Returns unique items in a slice
func UniqueInts(slice []int) []int {
	return RemoveDuplicate(slice)
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

// SplitGroup TODO
func SplitGroup(laxiconid []string, subGroupLength int64) [][]string {
	max := int64(len(laxiconid))
	var segmens = make([][]string, 0)
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

// RemoveEmpty 过滤掉空字符串
func CleanStrElems(elems []string) []string {
	var result []string
	for _, item := range elems {
		if strings.TrimSpace(item) != "" {
			result = append(result, strings.TrimSpace(item))
		}
	}
	return result
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
