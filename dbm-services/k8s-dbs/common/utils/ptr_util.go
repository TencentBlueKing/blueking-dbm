/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package utils

// IntPtr 获取 Int 类型指针
func IntPtr(v int) *int {
	return &v
}

// Int8Ptr 获取 int8 类型指针
func Int8Ptr(v int8) *int8 {
	return &v
}

// Int16Ptr 获取 int16 类型指针
func Int16Ptr(v int16) *int16 {
	return &v
}

// Int32Ptr 获取 Int类型 指针
func Int32Ptr(v int32) *int32 {
	return &v
}

// Int64Ptr 获取 int64 类型指针
func Int64Ptr(v int64) *int64 {
	return &v
}

// UintPtr 获取 uint 类型指针
func UintPtr(v uint) *uint {
	return &v
}

// Uint8Ptr 获取 uint8 类型指针
func Uint8Ptr(v uint8) *uint8 {
	return &v
}

// Uint16Ptr 获取 uint16 类型指针
func Uint16Ptr(v uint16) *uint16 {
	return &v
}

// Uint32Ptr 获取 uint32 类型指针
func Uint32Ptr(v uint32) *uint32 {
	return &v
}

// Uint64Ptr 获取 uint64 类型指针
func Uint64Ptr(v uint64) *uint64 {
	return &v
}

// Uintptr 获取 uintptr 类型指针
func Uintptr(v uintptr) *uintptr {
	return &v
}

// Float32Ptr 获取 float32 类型指针
func Float32Ptr(v float32) *float32 {
	return &v
}

// Float64Ptr 获取 float64 类型指针
func Float64Ptr(v float64) *float64 {
	return &v
}

// StringPtr 获取 string 类型指针
func StringPtr(v string) *string {
	return &v
}

// BoolPtr 获取 bool 类型指针
func BoolPtr(v bool) *bool {
	return &v
}

// BytePtr 获取 byte 类型指针
func BytePtr(v byte) *byte {
	return &v
}

// RunePtr 获取 rune 类型指针
func RunePtr(v rune) *rune {
	return &v
}
