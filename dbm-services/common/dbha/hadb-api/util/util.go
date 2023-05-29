// Package util TODO
package util

import (
	"reflect"
	"strings"
)

// FieldByNameCaseIgnore TODO
func FieldByNameCaseIgnore(v reflect.Type, name string) (reflect.StructField, bool) {
	name = strings.ToLower(name)
	v.Field(0)
	if name != "" {
		for i := 0; i < v.NumField(); i++ {
			tf := v.Field(i)
			if strings.ToLower(tf.Name) == name {
				return tf, true
			}
		}

	}

	return v.FieldByNameFunc(func(s string) bool {
		return strings.ToLower(s) == name
	})
}
