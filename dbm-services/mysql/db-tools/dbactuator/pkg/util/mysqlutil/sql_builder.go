package mysqlutil

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// UnsafeIn UnsafeBuilderStringIn ignore error
func UnsafeIn(in []string, quote string) string {
	inStr, _ := UnsafeBuilderStringIn(in, quote)
	return inStr
}

// UnsafeEqual UnsafeBuilderStringEqual ignore error
func UnsafeEqual(val string, quote string) string {
	inStr, _ := UnsafeBuilderStringEqual(val, quote)
	return inStr
}

// UnsafeBuilderStringIn godoc
// 将 string list 转成 in (?) 格式
// ['a', 'b'] to string 'a', 'b'. quote: '或者"
// 限制: 值不能包含特定字符, 输入只能是[]string, []int
func UnsafeBuilderStringIn(in []string, quote string) (string, error) {
	if len(in) == 0 {
		return "", nil
	}
	newIn := make([]string, len(in))
	unSafeRunes := "\"\\'`,;()"
	unSafeStrings := regexp.MustCompile("(?i)sleep|delimiter|call")
	for i, val := range in {
		if strings.ContainsAny(val, unSafeRunes) || unSafeStrings.MatchString(val) {
			return "", fmt.Errorf("unsafe value %s", val)
		}
		newIn[i] = quote + val + quote
	}
	return strings.Join(newIn, ","), nil
}

// UnsafeBuilderIntIn godoc
func UnsafeBuilderIntIn(in []int, quote string) string {
	if len(in) == 0 {
		return ""
	}
	newIn := make([]string, len(in))
	for i, val := range in {
		valStr := strconv.Itoa(val)
		newIn[i] = valStr
	}
	return strings.Join(newIn, ",")
}

// UnsafeBuilderStringEqual godoc
// convert a to 'a'
func UnsafeBuilderStringEqual(val, quote string) (string, error) {
	if val == "" {
		return quote + quote, nil // "''"
	}
	unSafeRunes := "\"\\'`,;()"
	unSafeStrings := regexp.MustCompile("(?i)sleep|delimiter|call")
	if strings.ContainsAny(val, unSafeRunes) || unSafeStrings.MatchString(val) {
		return "", fmt.Errorf("unsafe value %s", val)
	}
	return quote + val + quote, nil
}
