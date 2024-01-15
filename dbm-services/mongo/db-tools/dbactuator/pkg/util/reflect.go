package util

import (
	"reflect"
	"runtime"
)

// GetTypeName 获取接口类型名
func GetTypeName(object interface{}) string {
	t := reflect.TypeOf(object)
	if t.Kind() == reflect.Ptr {
		return "*" + t.Elem().Name()
	}
	return t.Name()
}

// GetFunctionName 获取函数名
func GetFunctionName(i interface{}) string {
	return runtime.FuncForPC(reflect.ValueOf(i).Pointer()).Name()
}
