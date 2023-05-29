package util

import (
	"fmt"

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

// ToBoolExtE 扩展 bool string， 支持 y/Y yes/YES on/off
func ToBoolExtE(val interface{}) (bool, error) {
	return parseBool(val)
}

// ToBoolExt 扩展 bool string， 支持 y/Y yes/YES on/off
func ToBoolExt(val interface{}) bool {
	ret, _ := parseBool(val)
	return ret
}

// parseBool returns the boolean value represented by the string.
//
// It accepts 1, 1.0, t, T, TRUE, true, True, YES, yes, Yes,Y, y, ON, on, On,
// 0, 0.0, f, F, FALSE, false, False, NO, no, No, N,n, OFF, off, Off.
// Any other value returns an error.
// from: https://github.com/beego/beego/blob/master/core/config/config.go 扩展了 y/Y yes/YES on/off
func parseBool(val interface{}) (value bool, err error) {
	if val != nil {
		switch v := val.(type) {
		case bool:
			return v, nil
		case string:
			switch v {
			case "1", "t", "T", "true", "TRUE", "True", "YES", "yes", "Yes", "Y", "y", "ON", "on", "On":
				return true, nil
			case "0", "f", "F", "false", "FALSE", "False", "NO", "no", "No", "N", "n", "OFF", "off", "Off":
				return false, nil
			}
		case int8, int32, int64:
			strV := fmt.Sprintf("%d", v)
			if strV == "1" {
				return true, nil
			} else if strV == "0" {
				return false, nil
			}
		case float64:
			if v == 1.0 {
				return true, nil
			} else if v == 0.0 {
				return false, nil
			}
		}
		return false, fmt.Errorf("parsing %q: invalid syntax", val)
	}
	return false, fmt.Errorf("parsing <nil>: invalid syntax")
}
