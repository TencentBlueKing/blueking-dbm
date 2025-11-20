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

package util

// MapParamsWithMapping 替换 map 中的 key
//
//nolint:unused
func MapParamsWithMapping(rawParams map[string]interface{}, mapping map[string]string) map[string]interface{} {
	mappedParams := make(map[string]interface{})
	for rawKey, value := range rawParams {
		if newKey, exists := mapping[rawKey]; exists {
			mappedParams[newKey] = value
		}
		// 如果 rawKey 不在 mapping 中，则忽略该字段
	}
	return mappedParams
}
