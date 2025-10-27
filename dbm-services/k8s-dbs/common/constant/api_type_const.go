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

// API 组
const (
	APIGroupSystem     = "system"
	APIGroupAddon      = "addon"
	APIGroupCluster    = "cluster"
	APIGroupOpsRequest = "opsrequest"
	APIGroupComponent  = "component"
	APIGroupK8s        = "k8s"
	APIGroupMeta       = "meta"
	APIGroupUnknown    = "unknown"
)

const (
	APIHealth = "v4_dbs_health"
)

// addon api
const (
	APIAddonInstall   = "v4_dbs_addon_install"
	APIAddonUninstall = "v4_dbs_addon_uninstall"
	APIAddonUpgrade   = "v4_dbs_addon_upgrade"
)

// cluster api
const (
	APIClusterVScaling      = "v4_dbs_cluster_vscaling"
	APIClusterHScaling      = "v4_dbs_cluster_hscaling"
	APIClusterVExpansion    = "v4_dbs_cluster_vexpansion"
	APIClusterStart         = "v4_dbs_cluster_start"
	APIClusterReStart       = "v4_dbs_cluster_restart"
	APIClusterStop          = "v4_dbs_cluster_stop"
	APIClusterDelete        = "v4_dbs_cluster_delete"
	APIClusterCreate        = "v4_dbs_cluster_create"
	APIClusterUpgrade       = "v4_dbs_cluster_upgrade"
	APIClusterUpdate        = "v4_dbs_cluster_update"
	APIClusterPartialUpdate = "v4_dbs_cluster_partial_update"
	APIClusterDesc          = "v4_dbs_cluster_desc"
	APIClusterStatus        = "v4_dbs_cluster_status"
	APIClusterExpose        = "v4_dbs_cluster_expose"
	APIClusterEventList     = "v4_dbs_cluster_event_list"
	APIClusterServiceInfo   = "v4_dbs_cluster_service_info"
)

// opsrequest api
const (
	APIOpsRequestDesc   = "v4_dbs_opsrequest_desc"
	APIOpsRequestStatus = "v4_dbs_opsrequest_status"
)

// component api
const (
	APIComponentDesc        = "v4_dbs_component_desc"
	APIComponentPods        = "v4_dbs_component_pods"
	APIComponentServiceInfo = "v4_dbs_component_service_info"
)

// k8s api
const (
	APIK8sNsCreate   = "v4_dbs_k8s_namespace_create"
	APIK8sPodDelete  = "v4_dbs_k8s_pod_delete"
	APIK8sPodDetail  = "v4_dbs_k8s_pod_detail"
	APIK8sPodLogList = "v4_dbs_k8s_pod_log_list"
	APIK8sPodRawLog  = "v4_dbs_k8s_pod_raw_log"
)

// meta api
const (
	APIMetaAddonCategoryCreate = "v4_dbs_metadata_addon_category_create"
	APIMetaAddonCategoryList   = "v4_dbs_metadata_addon_category_list"
)

// APIGroups 存储 API 名称到分组的映射
var APIGroups = initAPIGroups()

// 初始化 API 分组
func initAPIGroups() map[string]string {
	groups := make(map[string]string)

	add := func(group string, apis ...string) {
		for _, api := range apis {
			groups[api] = group
		}
	}

	add(APIGroupSystem, APIHealth)

	add(APIGroupAddon,
		APIAddonInstall,
		APIAddonUninstall,
		APIAddonUpgrade,
	)

	add(APIGroupCluster,
		APIClusterVScaling,
		APIClusterHScaling,
		APIClusterVExpansion,
		APIClusterStart,
		APIClusterReStart,
		APIClusterStop,
		APIClusterDelete,
		APIClusterCreate,
		APIClusterUpgrade,
		APIClusterUpdate,
		APIClusterPartialUpdate,
		APIClusterDesc,
		APIClusterStatus,
		APIClusterExpose,
		APIClusterEventList,
		APIClusterServiceInfo,
	)

	add(APIGroupOpsRequest,
		APIOpsRequestDesc,
		APIOpsRequestStatus,
	)

	add(APIGroupComponent,
		APIComponentDesc,
		APIComponentPods,
		APIComponentServiceInfo,
	)

	add(APIGroupK8s,
		APIK8sNsCreate,
		APIK8sPodDelete,
		APIK8sPodDetail,
		APIK8sPodLogList,
		APIK8sPodRawLog,
	)

	add(APIGroupMeta,
		APIMetaAddonCategoryCreate,
		APIMetaAddonCategoryList,
	)

	return groups
}

// GetAPIGroup 根据 API 名称获取所属分组
func GetAPIGroup(apiName string) string {
	if group, exists := APIGroups[apiName]; exists {
		return group
	}
	return APIGroupUnknown
}
