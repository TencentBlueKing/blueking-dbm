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

import "time"

// ResourceInGlobal 全局资源集合
var ResourceInGlobal = map[string]struct{}{
	ClusterDefinition:   {},
	ComponentDefinition: {},
	ComponentVersion:    {},
}

// Helm 默认配置
const (
	AddonDefaultNamespace = "kb-system"
	HelmOperationTimeout  = 30 * time.Second
	HelmDriver            = "secrets"
)

// KubeBlocks 环境变量名常量
const (
	KbPodName   = "KB_POD_NAME"
	KbPodUID    = "KB_POD_UID"
	KbNamespace = "KB_NAMESPACE"
	KbSaName    = "KB_SA_NAME"
	KbNodename  = "KB_NODENAME"
	KbHostIP    = "KB_HOST_IP"
	KbPodIP     = "KB_POD_IP"
	KbPodIps    = "KB_POD_IPS"
	KbHostip    = "KB_HOSTIP"
	KbPodip     = "KB_PODIP"
	KbPodips    = "KB_PODIPS"
)

// KbEnvVar KubeBlocks 识别的环境变量集合
var KbEnvVar = map[string]struct{}{
	KbPodName:   {},
	KbPodUID:    {},
	KbNamespace: {},
	KbSaName:    {},
	KbNodename:  {},
	KbHostIP:    {},
	KbPodIP:     {},
	KbPodIps:    {},
	KbHostip:    {},
	KbPodip:     {},
	KbPodips:    {},
}

// PodSelectLabel pod 选择器标签映射
var PodSelectLabel = map[string]string{
	"pod-name":  "apps.kubeblocks.io/pod-name",
	"component": "app.kubernetes.io/component",
	"role":      "kubeblocks.io/role",
}
