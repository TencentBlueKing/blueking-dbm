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

// DBM 相关环境变量常量定义
const (
	// AsyncToDBMEnv 控制是否启用异步同步到DBM的环境变量名
	AsyncToDBMEnv = "ASYNC_TO_DBM"
	// AsyncToDBMEnabled 表示启用异步同步的值
	AsyncToDBMEnabled = "true"
)

// ClusterOperationType 集群操作类型
// 定义集群同步操作的类型，确保类型安全
type ClusterOperationType string

const (
	// OperationCreate 创建集群操作
	OperationCreate ClusterOperationType = "create"
	// OperationDelete 删除集群操作
	OperationDelete ClusterOperationType = "delete"
	// OperationExpose 暴露集群服务操作
	OperationExpose ClusterOperationType = "expose"
	// OperationStop 停止集群操作
	OperationStop ClusterOperationType = "stop"
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
	StatusNormal   ClusterStatus = "normal"
	StatusUnNormal ClusterStatus = "unnormal" // nolint
)
