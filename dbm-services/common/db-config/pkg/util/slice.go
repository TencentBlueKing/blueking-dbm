package util

import (
	"reflect"
	"strconv"
	"strings"

	"github.com/pkg/errors"
)

var (
	// ErrConvertFail TODO
	ErrConvertFail = errors.New("convert data type is failure")
)

// Reverse string slice [site user info 0] -> [0 info user site]
func Reverse(ss []string) {
	ln := len(ss)
	for i := 0; i < ln/2; i++ {
		li := ln - i - 1
		// fmt.Println(i, "<=>", li)
		ss[i], ss[li] = ss[li], ss[i]
	}
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

// StringsToInts string slice to int slice
func StringsToInts(ss []string) (ints []int, err error) {
	for _, str := range ss {
		iVal, err := strconv.Atoi(str)
		if err != nil {
			return []int{}, err
		}

		ints = append(ints, iVal)
	}
	return
}

// TrimStrings trim string slice item.
func TrimStrings(ss []string, cutSet ...string) (ns []string) {
	hasCutSet := len(cutSet) > 0 && cutSet[0] != ""

	for _, str := range ss {
		if hasCutSet {
			ns = append(ns, strings.Trim(str, cutSet[0]))
		} else {
			ns = append(ns, strings.TrimSpace(str))
		}
	}
	return
}

// IntsHas check the []int contains the given value
func IntsHas(ints []int, val int) bool {
	for _, ele := range ints {
		if ele == val {
			return true
		}
	}
	return false
}

// Int64sHas check the []int64 contains the given value
func Int64sHas(ints []int64, val int64) bool {
	for _, ele := range ints {
		if ele == val {
			return true
		}
	}
	return false
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

// Contains assert array(strings, intXs, uintXs) should be contains the given value(int(X),string).
func Contains(arr, val interface{}) bool {
	if val == nil || arr == nil {
		return false
	}

	// if is string value
	if strVal, ok := val.(string); ok {
		if ss, ok := arr.([]string); ok {
			return StringsHas(ss, strVal)
		}

		rv := reflect.ValueOf(arr)
		if rv.Kind() == reflect.Slice || rv.Kind() == reflect.Array {
			for i := 0; i < rv.Len(); i++ {
				if v, ok := rv.Index(i).Interface().(string); ok && strings.EqualFold(v, strVal) {
					return true
				}
			}
		}

		return false
	}

	// as int value
	intVal, err := ToInt64(val)
	if err != nil {
		return false
	}

	if int64s, ok := toInt64Slice(arr); ok {
		return Int64sHas(int64s, intVal)
	}
	return false
}

// NotContains array(strings, ints, uints) should be not contains the given value.
func NotContains(arr, val interface{}) bool {
	return false == Contains(arr, val)
}

func toInt64Slice(arr interface{}) (ret []int64, ok bool) {
	rv := reflect.ValueOf(arr)
	if rv.Kind() != reflect.Slice && rv.Kind() != reflect.Array {
		return
	}

	for i := 0; i < rv.Len(); i++ {
		i64, err := ToInt64(rv.Index(i).Interface())
		if err != nil {
			return []int64{}, false
		}

		ret = append(ret, i64)
	}

	ok = true
	return
}

// ToInt64 convert string to int64
func ToInt64(in interface{}) (i64 int64, err error) {
	switch tVal := in.(type) {
	case nil:
		i64 = 0
	case string:
		i64, err = strconv.ParseInt(strings.TrimSpace(tVal), 10, 0)
	case int:
		i64 = int64(tVal)
	case int8:
		i64 = int64(tVal)
	case int16:
		i64 = int64(tVal)
	case int32:
		i64 = int64(tVal)
	case int64:
		i64 = tVal
	case uint:
		i64 = int64(tVal)
	case uint8:
		i64 = int64(tVal)
	case uint16:
		i64 = int64(tVal)
	case uint32:
		i64 = int64(tVal)
	case uint64:
		i64 = int64(tVal)
	case float32:
		i64 = int64(tVal)
	case float64:
		i64 = int64(tVal)
	default:
		err = ErrConvertFail
	}
	return
}

// MinValueInArry TODO
func MinValueInArry(arry []uint64) (minv uint64) {
	if len(arry) < 1 {
		return 0
	}
	minv = arry[0]
	for _, v := range arry {
		if v <= minv {
			minv = v
		}
	}
	return
}

// IsMinInArry TODO
func IsMinInArry(ele uint64, arry []uint64) bool {
	return ele <= uint64(MinValueInArry(arry))
}

// SliceUniq TODO
func SliceUniq(input []string) []string {
	newData := []string{}
	if len(input) > 0 {
		temp := make(map[string]struct{})
		for _, value := range input {
			temp[value] = struct{}{}
		}
		for k, _ := range temp {
			newData = append(newData, k)
		}
	}
	return newData
}

// SliceUniqMap TODO
// with order
func SliceUniqMap(s []string) []string {
	seen := make(map[string]bool, len(s))
	j := 0
	for _, v := range s {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = true
		s[j] = v
		j++
	}
	return s[:j]
}

// SliceErrorsToError TODO
func SliceErrorsToError(errs []error) error {
	var errStrs []string
	for _, e := range errs {
		errStrs = append(errStrs, e.Error())
	}
	errString := strings.Join(errStrs, "\n")
	return errors.New(errString)
}

// IsSlice TODO
func IsSlice(v interface{}) bool {
	return reflect.TypeOf(v).Kind() == reflect.Slice
}
