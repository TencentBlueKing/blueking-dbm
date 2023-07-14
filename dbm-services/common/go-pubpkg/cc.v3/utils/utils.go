/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package utils TODO
package utils

import (
	"reflect"
	"strings"
)

// GetStructTagName TODO
func GetStructTagName(t reflect.Type) []string {
	var tags []string
	switch t.Kind() {
	case reflect.Array, reflect.Chan, reflect.Map, reflect.Ptr, reflect.Slice:
		for _, item := range GetStructTagName(t.Elem()) {
			tags = append(tags, toTagName(item))
		}
	case reflect.Struct:
		for i := 0; i < t.NumField(); i++ {
			f := t.Field(i)
			switch f.Type.Kind() {
			case reflect.Array, reflect.Chan, reflect.Map, reflect.Ptr, reflect.Slice:
				for _, item := range GetStructTagName(f.Type) {
					tags = append(tags, toTagName(item))
				}
			}
			if f.Tag != "" {
				tags = append(tags, toTagName(f.Tag.Get("json")))
			}
		}
	}
	return tags
}

func toTagName(val string) string {
	parts := strings.Split(val, ",")
	if len(parts) > 0 {
		return parts[0]
	}
	return val
}
