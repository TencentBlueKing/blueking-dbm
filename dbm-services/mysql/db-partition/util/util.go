// Package util TODO
package util

import (
	"log/slog"
	"reflect"
	"regexp"
	"strings"
)

// HasElem 元素是否在数组中存在
func HasElem(elem interface{}, slice interface{}) bool {
	defer func() {
		if err := recover(); err != nil {
			slog.Error("HasElem error", err)
		}
	}()
	arrV := reflect.ValueOf(slice)
	if arrV.Kind() == reflect.Slice || arrV.Kind() == reflect.Array {
		for i := 0; i < arrV.Len(); i++ {
			// XXX - panics if slice element points to an unexported struct field
			// see https://golang.org/pkg/reflect/#Value.Interface
			if arrV.Index(i).Interface() == elem {
				return true
			}
		}
	}
	return false
}

// SplitName TODO
// //切分用户传过来的IP字符串列表等
// //切分规则：
// //把\r+|\s+|;+|\n+|,+这些分隔符，转成字符串数组
// //返回字符串数组
func SplitName(input string) ([]string, error) {
	result := []string{}
	if reg, err := regexp.Compile(`\r+|\s+|;+|\n+`); err != nil {
		return result, err
	} else {
		// 若返回正确的正则表达式，则将分隔符换为 ,
		input = reg.ReplaceAllString(input, ",")
	}
	if reg, err := regexp.Compile(`^,+|,+$`); err != nil {
		return result, err
	} else {
		input = reg.ReplaceAllString(input, "")
	}
	if reg, err := regexp.Compile(`,+`); err != nil {
		return result, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	result = strings.Split(input, ",")
	return result, nil
}

// SplitArray 切分数组为指定长度的子数组集合
func SplitArray(arr []string, length int) [][]string {
	var tmp [][]string
	mod := len(arr) % length
	k := len(arr) / length
	var round int
	if mod == 0 {
		round = k
	} else {
		round = k + 1
	}
	for i := 0; i < round; i++ {
		if i != k {
			tmp = append(tmp, arr[i*length:(i+1)*length])
		} else {
			tmp = append(tmp, arr[i*length:])
		}
	}
	return tmp
}
