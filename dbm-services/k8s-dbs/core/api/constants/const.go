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

package types

// response success
const (
	DescribeComponentSuccess   = "查询组件成功"
	DescribeClusterSuccess     = "查询集群成功"
	CreateClusterSuccess       = "申请创建集群成功"
	UpdateClusterSuccess       = "申请更新集群成功"
	DeleteClusterSuccess       = "申请删除集群成功"
	GetClusterStatusSuccess    = "查询集群状态成功"
	VerticalScalingSuccess     = "申请集群垂直扩缩容成功"
	HorizontalScalingSuccess   = "申请集群水平扩缩容成功"
	StartClusterSuccess        = "申请集群启动成功"
	StopClusterSuccess         = "申请集群停止成功"
	RestartClusterSuccess      = "申请集群重启成功"
	UpgradeClusterSuccess      = "申请集群升级成功"
	VolumeExpansionSuccess     = "申请集群磁盘扩容成功"
	ExposeClusterSuccess       = "申请集群暴露服务成功"
	DescribeOpsRequestSuccess  = "查询操作成功"
	GetOpsRequestStatusSuccess = "查询操作状态成功"
)
