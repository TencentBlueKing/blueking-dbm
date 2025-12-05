/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package converter provides type conversion utilities for common data types.
// It includes safe conversion functions for numbers, strings, and JSON serialization.
package converter

import (
	"encoding/json"
	"fmt"
	"strconv"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Number defines supported numeric types for conversion functions.
// It includes integer, unsigned integer, float, and string representations.
type Number interface {
	int | uint | int64 | uint64 | float64 | string
}

// ToInt converts a value to an integer.
func ToInt[T Number](value T) (int, error) {
	switch v := any(value).(type) {
	case int:
		return v, nil

	case uint:
		return int(v), nil

	case uint64:
		return int(v), nil

	case string:
		return strconv.Atoi(v)

	default:
		return 0, gerrors.Newf(gerrors.Unsupported, "Unsupported type: %T", value)
	}
}

// ToInt64 converts a value to an int64.
func ToInt64[T Number](value T) (int64, error) {
	switch v := any(value).(type) {
	case int:
		return int64(v), nil

	case uint:
		return int64(v), nil

	case int64:
		return v, nil

	case string:
		return strconv.ParseInt(v, 10, 64)

	default:
		return 0, gerrors.Newf(gerrors.Unsupported, "Unsupported type: %T", value)
	}
}

// ToUint64 converts a value to an uint64.
func ToUint64[T Number](value T) (uint64, error) {
	switch v := any(value).(type) {
	case int:
		return uint64(v), nil

	case uint:
		return uint64(v), nil

	case uint64:
		return v, nil

	case string:
		return strconv.ParseUint(v, 10, 64)

	default:
		return 0, gerrors.Newf(gerrors.Unsupported, "Unsupported type: %T", value)
	}
}

// ToFloat64 converts a value to an float64.
func ToFloat64[T Number](value T) (float64, error) {
	switch v := any(value).(type) {
	case float32:
		return float64(v), nil

	case float64:
		return float64(v), nil

	case string:
		rval, err := strconv.ParseFloat(v, 64)
		if err != nil {
			return 0, err
		}
		return float64(rval), nil

	default:
		return 0, gerrors.Newf(gerrors.Unsupported, "Unsupported type: %T", value)
	}
}

// ToUint converts a value to an uint.
func ToUint[T Number](value T) (uint, error) {
	switch v := any(value).(type) {
	case int:
		return uint(v), nil

	case uint:
		return v, nil

	case uint64:
		return uint(v), nil

	case string:
		rval, err := strconv.ParseUint(v, 10, 0)
		if err != nil {
			return 0, err
		}
		return uint(rval), nil

	default:
		return 0, gerrors.Newf(gerrors.Unsupported, "Unsupported type: %T", value)
	}
}

// To converts a value to the specified type.
func To[T any](v interface{}) (T, error) {
	if t, ok := v.(T); ok {
		return t, nil
	}

	var zero T
	return zero, gerrors.Newf(gerrors.Failure, "can not convert %T to %T", v, zero)
}

// ToJsonStr converts any value to formatted JSON string with indentation
func ToJsonStr(v interface{}) (string, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", gerrors.Newf(gerrors.InvalidParameter,
			"failed to marshal data: %s", err.Error())
	}
	return string(data), nil
}

// ToJsonLine converts any value to compact single-line JSON string
func ToJsonLine(v interface{}) (string, error) {
	data, err := json.Marshal(v)
	if err != nil {
		return "", gerrors.Newf(gerrors.InvalidParameter,
			"failed to marshal data: %s", err.Error())
	}
	return string(data), nil
}

// ToStrIgnoreErr safely converts any value to string, ignoring JSON marshaling errors.
func ToStrIgnoreErr(v interface{}) string {
	vStr, err := ToJsonLine(v)
	if err != nil {
		return fmt.Sprintf("%v", v)
	}
	return vStr
}
