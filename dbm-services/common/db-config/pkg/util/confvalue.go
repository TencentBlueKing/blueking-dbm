package util

import "strings"

// ConfValueIsPlaceHolder 判断 conf_value 是不是一个变量，当前认为 {{xxx}} 格式则为变量
func ConfValueIsPlaceHolder(s string) bool {
	if strings.HasPrefix(s, "{{") && strings.HasSuffix(s, "}}") {
		return true
	}
	return false
}
