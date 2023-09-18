package util

import (
	"fmt"
	"reflect"
	"sort"
	"strconv"
	"strings"

	"github.com/pkg/errors"
)

// 判断val 是否在elems 中
func ContainElem[T int | int64 | string](elems []T, val T) bool {
	for _, ele := range elems {
		if ele == val {
			return true
		}
	}
	return false
}

// IntsHas check the []int contains the given value
func IntsHas(ints []int, val int) bool {
	return ContainElem(ints, val)
}

// Int64sHas check the []int64 contains the given value
func Int64sHas(ints []int64, val int64) bool {
	return ContainElem(ints, val)
}

// StringsHas check the []string contains the given element
func StringsHas(ss []string, val string) bool {
	return ContainElem(ss, val)
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
	return UniqueSlice(slice)
}

// UniqueInts Returns unique items in a slice
func UniqueInts(slice []int) []int {
	return UniqueSlice(slice)
}

// IsConsecutiveStrings 是否是连续数字
// 如果存在 空元素 则报错
// 如果 isNumber=false, 则当做字符比较是否连续
func IsConsecutiveStrings(strList []string, isNumber bool) error {
	err := errors.New("not consecutive numbers")
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
			return errors.Errorf("illegal number %s", s)
		} else {
			intList[i] = d
		}
	}
	intList = UniqueInts(intList)
	sort.Ints(intList)
	count := len(intList)
	if (intList[count-1] - intList[0] + 1) != count {
		return err
	}
	return nil
}

// RemoveEmpty 过滤掉空字符串
func RemoveEmpty(input []string) []string {
	var result []string
	for _, item := range input {
		if strings.TrimSpace(item) != "" {
			result = append(result, item)
		}
	}
	return result
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

// StringsRemove an value form an string slice
func StringsRemove(ss []string, s string) []string {
	var ns []string
	for _, v := range ss {
		if v != s {
			ns = append(ns, v)
		}
	}

	return ns
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

// StrVal TODO
func StrVal(v interface{}) string {
	switch v := v.(type) {
	case string:
		return v
	case []byte:
		return string(v)
	case error:
		return v.Error()
	case fmt.Stringer:
		return v.String()
	default:
		return fmt.Sprintf("%v", v)
	}
}

// StrSlice TODO
func StrSlice(v interface{}) []string {
	switch v := v.(type) {
	case []string:
		return v
	case []interface{}:
		b := make([]string, 0, len(v))
		for _, s := range v {
			if s != nil {
				b = append(b, StrVal(s))
			}
		}
		return b
	default:
		val := reflect.ValueOf(v)
		switch val.Kind() {
		case reflect.Array, reflect.Slice:
			l := val.Len()
			b := make([]string, 0, l)
			for i := 0; i < l; i++ {
				value := val.Index(i).Interface()
				if value != nil {
					b = append(b, StrVal(value))
				}
			}
			return b
		default:
			if v == nil {
				return []string{}
			}

			return []string{StrVal(v)}
		}
	}
}
