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

import (
	"fmt"
	dbsErrors "k8s-dbs/errors"
)

// 描述 KB CRD
const (
	ClusterDefinition   = "ClusterDefinition"
	ComponentDefinition = "ComponentDefinition"
	ComponentVersion    = "ComponentVersion"
	Cluster             = "Cluster"
	OpsRequest          = "OpsRequest"
	BackupPolicy        = "BackupPolicy"
)

const APIVersion = "apps.kubeblocks.io/v1alpha1"
const DataProAPIVersion = "dataprotection.kubeblocks.io/v1alpha1"
const DefaultUserName = "admin"

const (
	DefaultRepoName       = "mapleleaf"
	DefaultRepoRepository = ""
)

// KubeBlocks_Labels
const (
	InstanceName  = "app.kubernetes.io/instance"
	ComponentName = "apps.kubeblocks.io/component-name"
	PodName       = "apps.kubeblocks.io/pod-name"
	ManagedBy     = "app.kubernetes.io/managed-by"
	ServiceType   = "dbs_k8s_service_type"
)

// Kubeblocks kb 常量
const Kubeblocks = "kubeblocks"

type TerminationPolicy string

const (
	DoNotTerminate TerminationPolicy = "DoNotTerminate"
	Halt           TerminationPolicy = "Halt"
	Delete         TerminationPolicy = "Delete"
	WipeOut        TerminationPolicy = "WipeOut"
)

// UnmarshalText 自定义 TerminationPolicy UnmarshalText 实现
func (t *TerminationPolicy) UnmarshalText(input []byte) error {
	val := string(input)
	switch val {
	case "DoNotTerminate":
		*t = DoNotTerminate
		return nil
	case "Halt":
		*t = Halt
		return nil
	case "Delete":
		*t = Delete
		return nil
	case "WipeOut":
		*t = WipeOut
		return nil
	default:
		return dbsErrors.NewK8sDbsError(dbsErrors.ParameterInvalidError,
			fmt.Errorf("不支持的集群删除策略: %s", val))
	}
}
