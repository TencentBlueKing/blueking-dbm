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

package addonoperation

import coreentity "k8s-dbs/core/entity"

// AddonType 定义存储类型
type AddonType string

// AddonComponent 定义存储组件
type AddonComponent string

type OperationType string

// AddonType 常量定义
const (
	AddonVM        AddonType = "victoriametrics"
	AddonSurrealDB AddonType = "surrealdb"
	AddonMilvus    AddonType = "milvus"
)

// VM 组件定义
const (
	ComponentVMStorage AddonComponent = "vmstorage"
	ComponentVMSelect  AddonComponent = "vmselect"
	ComponentVMInsert  AddonComponent = "vminsert"
)

// Surreal 组件定义
const (
	ComponentSurrealDB   AddonComponent = "surreal"
	ComponentSurrealTikv AddonComponent = "tikv"
	ComponentSurrealPd   AddonComponent = "pd"
)

// Milvus 组件定义
const (
	ComponentDataCoord  AddonComponent = "datacoord"
	ComponentDataNode   AddonComponent = "datanode"
	ComponentIndexCoord AddonComponent = "indexcoord"
	ComponentIndexNode  AddonComponent = "indexnode"
	ComponentQueryCoord AddonComponent = "querycoord"
	ComponentQueryNode  AddonComponent = "querynode"
	ComponentRootCoord  AddonComponent = "rootcoord"
	ComponentAttu       AddonComponent = "attu"
	ComponentProxy      AddonComponent = "proxy"
)

const (
	CreateCluster        OperationType = "CreateCluster"
	DeleteCluster        OperationType = "DeleteCluster"
	UpdateCluster        OperationType = "UpdateCluster"
	PartialUpdateCluster OperationType = "PartialUpdateCluster"
	StartCluster         OperationType = "StartCluster"
	StopCluster          OperationType = "StopCluster"
	RestartCluster       OperationType = "RestartCluster"
	StartComp            OperationType = "StartComponent"
	StopComp             OperationType = "StopComponent"
	RestartComp          OperationType = "RestartComponent"
	VScaling             OperationType = "VerticalScaling"
	HScaling             OperationType = "HorizontalScaling"
	VExpansion           OperationType = "VolumeExpansion"
	UpgradeComp          OperationType = "UpgradeComp"
	ExposeService        OperationType = "ExposeService"
	CreateK8sNs          OperationType = "CreateK8sNamespace"
	DeleteK8sPod         OperationType = "DeleteK8sPod"
)

// OperationCheckFunc 存储操作检查函数
type OperationCheckFunc func(
	operation OperationType,
	request *coreentity.Request,
) (bool, error)
