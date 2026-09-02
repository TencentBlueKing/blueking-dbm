/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package partitionsvr

import "time"

const DiffOneDay = 1

// 执行超时时间 单位：秒 注意不能直接格式化为int
// 这里超时退出只是act执行退出，mysql内连接无法释放
// 5分钟
const ExecTimeout = 300 * time.Second

// 锁等待超时时间 单位：秒
// 1分钟
const LockWaitTimeout = 60

// PartitionExecuteResult 分区执行结果
type PartitionExecuteResult struct {
	ExecuteResults []*ExecuteResult `json:"execute_results"`
}

type ExecuteResult struct {
	ConfigId   int                 `json:"config_id"`
	SubResults []*ExecuteOneResult `json:"sub_results"`
}

type ExecuteOneResult struct {
	DbName     string `json:"db_name"`
	TbName     string `json:"tb_name"`
	Status     bool   `json:"status"`
	ExecuteLog string `json:"execute_log"`
}

// Cluster 集群信息
type Cluster struct {
	BkBizId     int64  `json:"bk_biz_id"`
	ClusterID   int64  `json:"cluster_id"`
	BkCloudID   int    `json:"bk_cloud_id"`
	ClusterType string `json:"cluster_type"`
	IP          string `json:"ip"`
	Port        int    `json:"port"`
	ShardInfos  []*ShardInfo
	ErrorLog    []error
}

// ShardInfo 分片信息
type ShardInfo struct {
	IP      string `json:"ip"`
	Port    int    `json:"port"`
	Account string `json:"account"`
	PWD     string `json:"pwd"`
	ShardID int    `json:"shard_id"`
}

// PartitionDetail 单个库表的信息
// 真实的库表名称，区分于分区配置里可能的模糊匹配
type PartitionDetail struct {
	DbName        string
	TbName        string
	IsPartitioned bool // 当前表是否已经是分区表
	HasUniqueKey  bool // 是否有唯一键，pt工具需要表有唯一键才能使用 只在初始化时候使用 已是分区表的忽略
	NeedsReInit   bool // 已经是分区表，是否需要重新初始化表
	// ErrorLog      []error // 具体执行一个库表的 记录执行过程的错误 可能是初始化分区报错 添加分区报错 减少分区报错
}

// PartitionInfo 分区信息
type PartitionInfo struct {
	PartExpr   string // PARTITION_EXPRESSION
	PartMethod string // PARTITION_METHOD
	PartName   string // PARTITION_NAME
}

type TdbhaPartConf struct {
	PartitionConfig
	PartitionExecSummary *TdbhaExecSummary `json:"partition_exec_summary"` // 分区执行错误信息
}

type TdbCluPartConf struct {
	PartitionConfig
	PartitionExecSummary *TdbCluExecSummary `json:"partition_exec_summary"` // 分区执行错误信息
}

// PartitionExecSummary 记录单个分区配置的执行结果和错误信息
type TdbhaExecSummary struct {
	ConfigID        int64                     `json:"config_id"`         // 分区配置ID
	Status          bool                      `json:"status"`            // 配置整体执行是否成功
	TableCheckError error                     `json:"table_check_error"` // 目标库表校验相关错误，如库表不存在、无法改造为分区表等
	TableExecInfos  []*PartitionTableExecInfo `json:"table_exec_infos"`  // 每个库表的分区执行错误信息，可能模糊匹配多个库表
}

type TdbCluExecSummary struct {
	ConfigID     int64                   `json:"config_id"`     // 分区配置ID
	Status       bool                    `json:"status"`        // 配置整体执行是否成功 任意一个失败 都是false
	ShardResults []*PartitionShardResult `json:"shard_results"` // 每个分片的执行结果
}

// PartitionShardResult 记录单个分片的执行结果
type PartitionShardResult struct {
	ShardID         int                       `json:"shard_id"`          // 分片ID
	ShardIP         string                    `json:"shard_ip"`          // 分片IP
	ShardPort       int                       `json:"shard_port"`        // 分片端口
	ShardStatus     bool                      `json:"shard_status"`      // 该分片执行是否成功
	ConnectionError error                     `json:"connection_error"`  // 分片连接错误
	TableCheckError error                     `json:"table_check_error"` // 目标库表校验相关错误，如库表不存在、无法改造为分区表等
	TableExecInfos  []*PartitionTableExecInfo `json:"table_exec_infos"`  // 该分片下的表执行结果
}

// PartitionTableError 记录单个库表的分区执行结果和详细错误
type PartitionTableExecInfo struct {
	DbName          string               `json:"db_name"`           // 库名
	TbName          string               `json:"tb_name"`           // 表名
	Status          bool                 `json:"status"`            // 该表分区操作是否成功
	TableCheckError error                `json:"table_check_error"` // 目标库表校验相关错误，如库表不存在、无法改造为分区表等
	StepInfos       []*PartitionStepInfo `json:"step_infos"`        // 分区各步骤的错误信息
}

// PartitionStepInfo 记录分区操作各步骤的错误信息
type PartitionStepInfo struct {
	Step      string `json:"step"`      // 步骤名称: init/add/drop
	Status    bool   `json:"status"`    // 该步骤是否成功
	Message   string `json:"message"`   // 错误信息描述
	Statement string `json:"statement"` // 执行的SQL语句
}
