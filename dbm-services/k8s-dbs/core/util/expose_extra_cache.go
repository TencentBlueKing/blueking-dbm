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

import "sync"

// exposeExtraCache 缓存 expose 请求中的 service 配置 JSON
// key: "namespace/clusterName", value: extra JSON string
var exposeExtraCache sync.Map

// StoreExposeExtra 缓存 expose 请求的 service JSON
func StoreExposeExtra(namespace, clusterName, extraJSON string) {
	key := namespace + "/" + clusterName
	exposeExtraCache.Store(key, extraJSON)
}

// LoadAndDeleteExposeExtra 获取并删除缓存的 expose service JSON（一次性消费）
func LoadAndDeleteExposeExtra(namespace, clusterName string) (string, bool) {
	key := namespace + "/" + clusterName
	val, ok := exposeExtraCache.LoadAndDelete(key)
	if !ok {
		return "", false
	}
	return val.(string), true
}
