package util

import (
	"github.com/spf13/cast"
)

// ToBoolE 使用 cast.ToBoolE
func ToBoolE(val interface{}) (bool, error) {
	return cast.ToBoolE(val)
}

// ToBool 使用 cast.ToBool
func ToBool(val interface{}) bool {
	return cast.ToBool(val)
}
