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

package i18n

// 系统错误消息
const (
	MsgErrAuth             = "error.auth"
	MsgErrServer           = "error.server"
	MsgErrEngineType       = "error.engine_type"
	MsgErrAuthorization    = "error.authorization"
	MsgErrThirdAPI         = "error.third_api"
	MsgErrResubmit         = "error.resubmit"
	MsgErrLogin            = "error.login"
	MsgErrLogout           = "error.logout"
	MsgErrCreateMetadata   = "error.create_metadata"
	MsgErrUpdateMetadata   = "error.update_metadata"
	MsgErrGetMetadata      = "error.get_metadata"
	MsgErrDeleteMetadata   = "error.delete_metadata"
	MsgErrParameterInvalid = "error.parameter_invalid"
	MsgErrParameterType    = "error.parameter_type"
	MsgErrParameterValue   = "error.parameter_value"
	MsgErrOperationForbid  = "error.operation_forbidden"
	MsgErrNotPermission    = "error.not_permission"
)

// 集群操作错误消息
const (
	MsgErrClusterDescribe      = "error.cluster.describe"
	MsgErrClusterCreate        = "error.cluster.create"
	MsgErrClusterGet           = "error.cluster.get"
	MsgErrClusterDelete        = "error.cluster.delete"
	MsgErrClusterGetStatus     = "error.cluster.get_status"
	MsgErrClusterGetEvent      = "error.cluster.get_event"
	MsgErrClusterVerticalScale = "error.cluster.vertical_scaling"
	MsgErrClusterHorizScale    = "error.cluster.horizontal_scaling"
	MsgErrClusterStart         = "error.cluster.start"
	MsgErrClusterStop          = "error.cluster.stop"
	MsgErrClusterRestart       = "error.cluster.restart"
	MsgErrClusterUpgrade       = "error.cluster.upgrade"
	MsgErrClusterVolumeExpand  = "error.cluster.volume_expansion"
	MsgErrClusterExpose        = "error.cluster.expose"
	MsgErrClusterDescribeOps   = "error.cluster.describe_ops"
	MsgErrClusterGetOpsStatus  = "error.cluster.get_ops_status"
	MsgErrClusterUpdate        = "error.cluster.update"
	MsgErrClusterPartialUpdate = "error.cluster.partial_update"
	MsgErrClusterGetSvc        = "error.cluster.get_svc"
)

// Kubernetes 操作错误消息
const (
	MsgErrK8sCreateNs     = "error.k8s.create_ns"
	MsgErrK8sDeleteNs     = "error.k8s.delete_ns"
	MsgErrK8sGetPodLog    = "error.k8s.get_pod_log"
	MsgErrK8sAPITimeout   = "error.k8s.api_timeout"
	MsgErrK8sGetPodDetail = "error.k8s.get_pod_detail"
	MsgErrK8sCreateClient = "error.k8s.create_client"
	MsgErrK8sDeletePod    = "error.k8s.delete_pod"
	MsgErrK8sInstallHelm  = "error.k8s.install_helm"
)

// 插件操作错误消息
const (
	MsgErrAddonInstall   = "error.addon.install"
	MsgErrAddonUninstall = "error.addon.uninstall"
	MsgErrAddonUpgrade   = "error.addon.upgrade"
)

// 组件操作错误消息
const (
	MsgErrComponentDescribe = "error.component.describe"
	MsgErrComponentGetSvc   = "error.component.get_svc"
	MsgErrComponentGetPods  = "error.component.get_pods"
)

// 校验消息
const (
	MsgValidationRequired  = "validation.required"
	MsgValidationInvalid   = "validation.invalid"
	MsgValidationMinLength = "validation.min_length"
	MsgValidationMaxLength = "validation.max_length"
)

// 格式化
const (
	MsgSeparator = "format.separator"
)
