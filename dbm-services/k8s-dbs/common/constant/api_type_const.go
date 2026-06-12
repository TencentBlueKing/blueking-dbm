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

// APIGroupSystem 系统管理相关 API 组标识
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

// APIHealth 系统健康检查接口标识
const (
	APIHealth = "v4_dbs_health"
)

// APIAddonInstall addon 安装接口标识
const (
	APIAddonInstall   = "v4_dbs_addon_install"
	APIAddonUninstall = "v4_dbs_addon_uninstall"
	APIAddonUpgrade   = "v4_dbs_addon_upgrade"
)

// APIClb clb接口
const (
	APIClbCreate = "v4_dbs_clb_create"
	APIClbGet    = "v4_dbs_clb_get"
)

// APIClusterCreate 集群管理相关接口标识
const (
	APIClusterVScaling      = "v4_dbs_cluster_vscaling"
	APIClusterHScaling      = "v4_dbs_cluster_hscaling"
	APIClusterVExpansion    = "v4_dbs_cluster_vexpansion"
	APIClusterStart         = "v4_dbs_cluster_start"
	APIClusterRestart       = "v4_dbs_cluster_restart"
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

// APIOpsRequestDesc 运维请求相关接口标识
const (
	APIOpsRequestDesc   = "v4_dbs_opsrequest_desc"
	APIOpsRequestStatus = "v4_dbs_opsrequest_status"
)

// APIComponentDesc 集群组件相关接口标识
const (
	APIComponentDesc        = "v4_dbs_component_desc"
	APIComponentPods        = "v4_dbs_component_pods"
	APIComponentServiceInfo = "v4_dbs_component_service_info"
)

// APIK8sNsCreate K8s 资源相关接口标识
const (
	APIK8sNsCreate   = "v4_dbs_k8s_namespace_create"
	APIK8sPodDelete  = "v4_dbs_k8s_pod_delete"
	APIK8sPodDetail  = "v4_dbs_k8s_pod_detail"
	APIK8sPodLogList = "v4_dbs_k8s_pod_log_list"
	APIK8sPodRawLog  = "v4_dbs_k8s_pod_raw_log"
)

// APIMetaAddonCategoryCreate addon 分类元数据接口标识
const (
	APIMetaAddonCategoryCreate = "v4_dbs_meta_addon_category_create"
	APIMetaAddonCategoryList   = "v4_dbs_meta_addon_category_list"
)

// APIMetaAddonList addon 元数据接口标识
const (
	APIMetaAddonList     = "v4_dbs_meta_addon_list"
	APIMetaAddonDetail   = "v4_dbs_meta_addon_detail"
	APIMetaAddonVersions = "v4_dbs_meta_addon_versions"
	APIMetaAddonCreate   = "v4_dbs_meta_addon_create"
	APIMetaAddonDelete   = "v4_dbs_meta_addon_delete"
	APIMetaAddonUpdate   = "v4_dbs_meta_addon_update"
)

// APIMetaAddonSpecPlanList addon 规格方案元数据接口标识
const (
	APIMetaAddonSpecPlanList   = "v4_dbs_meta_addon_spec_plan_list"
	APIMetaAddonSpecPlanDetail = "v4_dbs_meta_addon_spec_plan_detail"
	APIMetaAddonSpecPlanCreate = "v4_dbs_meta_addon_spec_plan_create"
	APIMetaAddonSpecPlanDelete = "v4_dbs_meta_addon_spec_plan_delete"
	APIMetaAddonSpecPlanUpdate = "v4_dbs_meta_addon_spec_plan_update"
)

// APIMetaComponentSpecPlanList 组件规格方案元数据接口标识
const (
	APIMetaComponentSpecPlanList   = "v4_dbs_meta_component_spec_plan_list"
	APIMetaComponentSpecPlanDetail = "v4_dbs_meta_component_spec_plan_detail"
	APIMetaComponentSpecPlanCreate = "v4_dbs_meta_component_spec_plan_create"
	APIMetaComponentSpecPlanDelete = "v4_dbs_meta_component_spec_plan_delete"
	APIMetaComponentSpecPlanUpdate = "v4_dbs_meta_component_spec_plan_update"
)

// APIMetaAddonRepoDetail addon 仓库元数据接口标识
const (
	APIMetaAddonRepoDetail = "v4_dbs_meta_addon_repo_detail"
	APIMetaAddonRepoSearch = "v4_dbs_meta_addon_repo_search"
	APIMetaAddonRepoCreate = "v4_dbs_meta_addon_repo_create"
)

// APIMetaAddonClusterRepoDetail addon 集群仓库元数据接口标识
const (
	APIMetaAddonClusterRepoDetail = "v4_dbs_meta_addon_cluster_repo_detail"
	APIMetaAddonClusterRepoSearch = "v4_dbs_meta_addon_cluster_repo_search"
	APIMetaAddonClusterRepoCreate = "v4_dbs_meta_addon_cluster_repo_create"
)

// APIMetaAddonTopoCreate addon 拓扑元数据接口标识
const (
	APIMetaAddonTopoCreate = "v4_dbs_meta_addon_topo_create"
	APIMetaAddonTopoDetail = "v4_dbs_meta_addon_topo_detail"
	APIMetaAddonTopoSearch = "v4_dbs_meta_addon_topo_search"
)

// APIMetaAddonTypeList addon 类型元数据接口标识
const (
	APIMetaAddonTypeList   = "v4_dbs_meta_addon_type_list"
	APIMetaAddonTypeCreate = "v4_dbs_meta_addon_type_create"
)

// APIMetaClusterRequestList 集群请求元数据接口标识
const (
	APIMetaClusterRequestList   = "v4_dbs_meta_cluster_request_list"
	APIMetaClusterRequestCreate = "v4_dbs_meta_cluster_request_create"
	APIMetaClusterRequestUpdate = "v4_dbs_meta_cluster_request_update"
)

// APIMetaClusterDetail 集群元数据接口标识
const (
	APIMetaClusterDetail            = "v4_dbs_meta_cluster_detail"
	APIMetaClusterDetailByClusterID = "v4_dbs_meta_cluster_detail_by_cluster_id"
	APIMetaClusterList              = "v4_dbs_meta_cluster_list"
	APIMetaClusterTopologyDetail    = "v4_dbs_meta_cluster_topology_detail"
)

// APIMetaComponentDetail 组件元数据接口标识
const (
	APIMetaComponentDetail = "v4_dbs_meta_component_detail"
)

// APIMetaClusterAddonDetail 集群 addon 元数据接口标识
const (
	APIMetaClusterAddonDetail = "v4_dbs_meta_cluster_addon_detail"
	APIMetaClusterAddonByName = "v4_dbs_meta_cluster_addon_name"
)

// APIMetaOpDefList 操作定义元数据接口标识
const (
	APIMetaOpDefList   = "v4_dbs_meta_op_def_list"
	APIMetaOpDefCreate = "v4_dbs_meta_op_def_create"
)

// APIMetaClusterOpDefList 集群操作定义元数据接口标识
const (
	APIMetaClusterOpDefList   = "v4_dbs_meta_cluster_op_def_list"
	APIMetaClusterOpDefCreate = "v4_dbs_meta_cluster_op_def_create"
)

// APIMetaComponentOpDefList 组件操作定义元数据接口标识
const (
	APIMetaComponentOpDefList   = "v4_dbs_meta_component_op_def_list"
	APIMetaComponentOpDefCreate = "v4_dbs_meta_component_op_def_create"
)

// APIMetaAcReleaseDetail 接入层发布元数据接口标识
const (
	APIMetaAcReleaseDetail = "v4_dbs_meta_ac_release_detail"
	APIMetaAcReleaseSearch = "v4_dbs_meta_ac_release_search"
)

// APIMetaAcVersionList 接入层版本元数据接口标识
const (
	APIMetaAcVersionList   = "v4_dbs_meta_ac_version_list"
	APIMetaAcVersionCreate = "v4_dbs_meta_ac_version_create"
	APIMetaAcVersionDelete = "v4_dbs_meta_ac_version_delete"
	APIMetaAcVersionDetail = "v4_dbs_meta_ac_version_detail"
	APIMetaAcVersionUpdate = "v4_dbs_meta_ac_version_update"
)

// APIMetaK8sConfigDetail K8s 配置元数据接口标识
const (
	APIMetaK8sConfigDetail       = "v4_dbs_meta_k8s_config_detail"
	APIMetaK8sConfigDetailByVis  = "v4_dbs_meta_k8s_config_detail_by_vis"
	APIMetaK8sConfigDetailByName = "v4_dbs_meta_k8s_config_detail_by_name"
	APIMetaK8sConfigCreate       = "v4_dbs_meta_k8s_config_create"
	APIMetaK8sConfigDelete       = "v4_dbs_meta_k8s_config_delete"
	APIMetaK8sConfigUpdate       = "v4_dbs_meta_k8s_config_update"
)

// APIMetaOpsRequestDetail 运维请求元数据接口标识
const (
	APIMetaOpsRequestDetail = "v4_dbs_meta_ops_request_detail"
)

// APIGroups 存储 API 名称到分组的映射
var APIGroups = initAPIGroups()

// add 向分组映射中添加 API 标识
func add(groups map[string]string, group string, apis ...string) {
	for _, api := range apis {
		groups[api] = group
	}
}

// initAPIGroups 初始化并返回 API 分组映射
func initAPIGroups() map[string]string {
	groups := make(map[string]string)

	initSystemGroups(groups)
	initAddonGroups(groups)
	initClusterGroups(groups)
	initOpsRequestGroups(groups)
	initComponentGroups(groups)
	initK8sGroups(groups)
	initMetaGroups(groups)

	return groups
}

func initSystemGroups(groups map[string]string) {
	add(groups, APIGroupSystem, APIHealth)
}

func initAddonGroups(groups map[string]string) {
	add(groups, APIGroupAddon,
		APIAddonInstall,
		APIAddonUninstall,
		APIAddonUpgrade,
	)
}

func initClusterGroups(groups map[string]string) {
	add(groups, APIGroupCluster,
		APIClusterVScaling,
		APIClusterHScaling,
		APIClusterVExpansion,
		APIClusterStart,
		APIClusterRestart,
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
}

func initOpsRequestGroups(groups map[string]string) {
	add(groups, APIGroupOpsRequest,
		APIOpsRequestDesc,
		APIOpsRequestStatus,
	)
}

func initComponentGroups(groups map[string]string) {
	add(groups, APIGroupComponent,
		APIComponentDesc,
		APIComponentPods,
		APIComponentServiceInfo,
	)
}

func initK8sGroups(groups map[string]string) {
	add(groups, APIGroupK8s,
		APIK8sNsCreate,
		APIK8sPodDelete,
		APIK8sPodDetail,
		APIK8sPodLogList,
		APIK8sPodRawLog,
	)
}

func initMetaGroups(groups map[string]string) {
	initAddonCategoryMetaGroups(groups)
	initAddonMetaGroups(groups)
	initAddonSpecPlanMetaGroups(groups)
	initComponentSpecPlanMetaGroups(groups)
	initAddonRepoMetaGroups(groups)
	initAddonClusterRepoMetaGroups(groups)
	initAddonTopoMetaGroups(groups)
	initAddonTypeMetaGroups(groups)
	initClusterRequestMetaGroups(groups)
	initClusterMetaGroups(groups)
	initComponentMetaGroups(groups)
	initClusterAddonMetaGroups(groups)
	initOpDefMetaGroups(groups)
	initClusterOpDefMetaGroups(groups)
	initComponentOpDefMetaGroups(groups)
	initAcReleaseMetaGroups(groups)
	initAcVersionMetaGroups(groups)
	initK8sConfigMetaGroups(groups)
	initOpsRequestMetaGroups(groups)
}

func initAddonCategoryMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonCategoryCreate,
		APIMetaAddonCategoryList,
	)
}

func initAddonMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonList,
		APIMetaAddonDetail,
		APIMetaAddonVersions,
		APIMetaAddonCreate,
		APIMetaAddonDelete,
		APIMetaAddonUpdate,
	)
}

func initAddonSpecPlanMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonSpecPlanList,
		APIMetaAddonSpecPlanDetail,
		APIMetaAddonSpecPlanCreate,
		APIMetaAddonSpecPlanDelete,
		APIMetaAddonSpecPlanUpdate,
	)
}

func initComponentSpecPlanMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaComponentSpecPlanList,
		APIMetaComponentSpecPlanDetail,
		APIMetaComponentSpecPlanCreate,
		APIMetaComponentSpecPlanDelete,
		APIMetaComponentSpecPlanUpdate,
	)
}

func initAddonRepoMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonRepoDetail,
		APIMetaAddonRepoSearch,
		APIMetaAddonRepoCreate,
	)
}

func initAddonClusterRepoMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonClusterRepoDetail,
		APIMetaAddonClusterRepoSearch,
		APIMetaAddonClusterRepoCreate,
	)
}

func initAddonTopoMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonTopoCreate,
		APIMetaAddonTopoDetail,
		APIMetaAddonTopoSearch,
	)
}

func initAddonTypeMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAddonTypeList,
		APIMetaAddonTypeCreate,
	)
}

func initClusterRequestMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaClusterRequestList,
		APIMetaClusterRequestCreate,
		APIMetaClusterRequestUpdate,
	)
}

func initClusterMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaClusterDetail,
		APIMetaClusterDetailByClusterID,
		APIMetaClusterList,
		APIMetaClusterTopologyDetail,
	)
}

func initComponentMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaComponentDetail,
	)
}

func initClusterAddonMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaClusterAddonDetail,
		APIMetaClusterAddonByName,
	)
}

func initOpDefMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaOpDefList,
		APIMetaOpDefCreate,
	)
}

func initClusterOpDefMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaClusterOpDefList,
		APIMetaClusterOpDefCreate,
	)
}

func initComponentOpDefMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaComponentOpDefList,
		APIMetaComponentOpDefCreate,
	)
}

func initAcReleaseMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAcReleaseDetail,
		APIMetaAcReleaseSearch,
	)
}

func initAcVersionMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaAcVersionList,
		APIMetaAcVersionCreate,
		APIMetaAcVersionDelete,
		APIMetaAcVersionDetail,
		APIMetaAcVersionUpdate,
	)
}

func initK8sConfigMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaK8sConfigDetail,
		APIMetaK8sConfigDetailByVis,
		APIMetaK8sConfigDetailByName,
		APIMetaK8sConfigCreate,
		APIMetaK8sConfigDelete,
		APIMetaK8sConfigUpdate,
	)
}

func initOpsRequestMetaGroups(groups map[string]string) {
	add(groups, APIGroupMeta,
		APIMetaOpsRequestDetail,
	)
}

// GetAPIGroup 根据 API 名称获取所属分组
func GetAPIGroup(apiName string) string {
	if group, exists := APIGroups[apiName]; exists {
		return group
	}
	return APIGroupUnknown
}
