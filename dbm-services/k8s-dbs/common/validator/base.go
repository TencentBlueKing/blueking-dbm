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

// Package validator 提供请求参数校验相关的工具函数
package validator

import (
	"reflect"
	"strings"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
)

// GetNestedField 获取嵌套字段
func GetNestedField(t reflect.Type, path []string) (reflect.StructField, bool) {
	if len(path) == 0 {
		return reflect.StructField{}, false
	}

	name := path[0]
	if strings.Contains(name, "[") {
		name = strings.Split(name, "[")[0]
	}
	// 处理指针类型
	if t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	field, ok := t.FieldByName(name)
	if !ok {
		return reflect.StructField{}, false
	}

	if len(path) == 1 {
		return field, true
	}

	fieldType := field.Type
	// 处理指针类型
	if fieldType.Kind() == reflect.Pointer {
		fieldType = fieldType.Elem()
	}
	// 处理切片类型
	if fieldType.Kind() == reflect.Slice {
		fieldType = fieldType.Elem()
	}
	return GetNestedField(fieldType, path[1:])
}

// ValidateError 检查是否是字段校验失败
//
// 消息选取优先级：
//  1. 若当前触发的校验 tag 在 TagMessages 中有专属消息（如 cpuRequestLteLimit），优先使用
//  2. 否则回退到字段上的 msg tag
//  3. 若字段无 msg tag，则使用 tag 兜底映射
//  4. 若均未匹配，则使用 fe.Error()
func ValidateError(err error, request any) (bool, string) {
	var ve validator.ValidationErrors
	if errors.As(err, &ve) {
		for _, fe := range ve {
			filedName := fe.StructNamespace()
			path := strings.Split(filedName, ".")[1:]
			field, ok := GetNestedField(reflect.TypeOf(request), path)
			if ok {
				if tagMsg, tagOK := TagMessages[fe.Tag()]; tagOK {
					return true, tagMsg
				}
				msg := field.Tag.Get("msg")
				if msg == "" {
					msg = fe.Error()
				}
				return true, msg
			}
			// 字段路径无法反射定位（例如结构体级校验），退化到 tag 兜底
			if tagMsg, tagOK := TagMessages[fe.Tag()]; tagOK {
				return true, tagMsg
			}
		}
	}
	return false, err.Error()
}
