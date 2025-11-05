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

package constant

var APIURLs = initAPIURLs()

func initAPIURLs() map[string]string {
	return map[string]string{
		"/v4/dbs/addon/install":   APIAddonInstall,
		"/v4/dbs/addon/uninstall": APIAddonUninstall,
		"/v4/dbs/addon/upgrade":   APIAddonUpgrade,

		"/v4/dbs/opsRequest/vscaling":   APIClusterVScaling,
		"/v4/dbs/opsRequest/hscaling":   APIClusterHScaling,
		"/v4/dbs/opsRequest/vexpansion": APIClusterVExpansion,
		"/v4/dbs/opsRequest/start":      APIClusterStart,
		"/v4/dbs/opsRequest/restart":    APIClusterReStart,
		"/v4/dbs/opsRequest/stop":       APIClusterStop,
		"/v4/dbs/opsRequest/upgrade":    APIClusterUpgrade,
		"/v4/dbs/opsRequest/expose":     APIClusterExpose,

		"/v4/dbs/cluster/delete":         APIClusterDelete,
		"/v4/dbs/cluster/create":         APIClusterCreate,
		"/v4/dbs/cluster/update":         APIClusterUpdate,
		"/v4/dbs/cluster/partial_update": APIClusterPartialUpdate,
		"/v4/dbs/cluster/service/info":   APIClusterServiceInfo,

		"/v4/dbs/k8s_cluster/namespace":  APIK8sNsCreate,
		"/v4/dbs/k8s_cluster/pod/delete": APIK8sPodDelete,

		"/v4/metadata/addon_category": APIMetaAddonCategoryCreate,

		"/v4/dbs/dataweb/cluster/config": APIClusterUpdate,
		"/v4/dbs/dataweb/cluster/create": APIClusterCreate,
		"/v4/dbs/dataweb/cluster/expose": APIClusterExpose,
	}
}

// GetAPIURL 根据 API 常量获取对应的 URL
func GetAPIURL(apiConst string) string {
	if url, exists := APIURLs[apiConst]; exists {
		return url
	}
	return ""
}
