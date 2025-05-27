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

// These constants define all supported cluster-level or component-level operation types
const (
	CreateCluster = "CreateCluster"
	DeleteCluster = "DeleteCluster"
	UpdateCluster = "UpdateCluster"

	StartCluster   = "StartCluster"
	StopCluster    = "StopCluster"
	RestartCluster = "RestartCluster"
	StartComp      = "StartComponent"
	StopComp       = "StopComponent"
	RestartComp    = "RestartComponent"
	VScaling       = "VerticalScaling"
	HScaling       = "HorizontalScaling"
	VExpansion     = "VolumeExpansion"
	UpgradeComp    = "UpgradeComp"
	ExposeService  = "ExposeService"

	CreateK8sNs = "CreateK8sNamespace"
)

// OpsRequest operation types
// These constants define the types of operations that can be performed through OpsRequest
const (
	Start             = "Start"
	Stop              = "Stop"
	Restart           = "Restart"
	Switchover        = "Switchover"
	VerticalScaling   = "VerticalScaling"
	HorizontalScaling = "HorizontalScaling"
	VolumeExpansion   = "VolumeExpansion"
	Reconfiguring     = "Reconfiguring"
	Upgrade           = "Upgrade"
	Backup            = "Backup"
	Restore           = "Restore"
	Expose            = "Expose"
	DataScript        = "DataScript"
	RebuildInstance   = "RebuildInstance"
	Custom            = "Custom"
)
