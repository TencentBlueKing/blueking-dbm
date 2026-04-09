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

// ClusterOperationType 集群操作类型
// 定义集群同步操作的类型，确保类型安全
type ClusterOperationType string

const (
	// OperationCreate 创建集群操作
	OperationCreate ClusterOperationType = "create"
	// OperationUpdate 更新集群操作
	OperationUpdate ClusterOperationType = "update"
	// OperationDelete 删除集群操作
	OperationDelete ClusterOperationType = "delete"
	// OperationExpose 暴露集群服务操作
	OperationExpose ClusterOperationType = "expose"
	// OperationStop 停止集群操作
	OperationStop ClusterOperationType = "stop"
	// OperationStart 启动集群操作
	OperationStart ClusterOperationType = "start"
	// OperationRestart 重启集群操作
	OperationRestart ClusterOperationType = "restart"
	// OperationHscaling 水平扩缩集群操作
	OperationHscaling ClusterOperationType = "hscaling"
	// OperationVscaling 垂直扩缩集群操作
	OperationVscaling ClusterOperationType = "vscaling"
	// OperationVolumeExpand 磁盘扩缩集群操作
	OperationVolumeExpand ClusterOperationType = "volume_expand"
	// OperationStatusAbnormal 集群更新为异常状态操作
	OperationStatusAbnormal ClusterOperationType = "status_abnormal"
	// OperationStatusNormal 集群更新为正常状态操作
	OperationStatusNormal ClusterOperationType = "status_normal" // nolint
)

// ClusterPhase 集群阶段
// 定义集群的生命周期阶段
type ClusterPhase string

const (
	// PhaseOnline 集群在线阶段
	PhaseOnline ClusterPhase = "online"
	// PhaseOffline 集群离线阶段
	PhaseOffline ClusterPhase = "offline"
)

// ClusterStatus 集群状态
// 定义集群的运行状态
type ClusterStatus string

const (
	// StatusNormal 集群正常状态
	StatusNormal ClusterStatus = "normal"
	// StatusAbNormal 集群异常状态
	StatusAbNormal ClusterStatus = "abnormal"
	// StatusTemporary 集群临时状态
	StatusTemporary ClusterStatus = "temporary" // nolint
)
