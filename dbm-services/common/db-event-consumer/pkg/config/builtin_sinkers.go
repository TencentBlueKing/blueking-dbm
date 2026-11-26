// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"fmt"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/cst"
	"dbm-services/common/db-event-consumer/pkg/model"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

// datasource 名称关键字。
// 这些名字与具体环境无关，每个环境在自己的 datasource.yaml 里把同名 datasource 指向真实的库。
const (
	// DsDbmReport 上报类数据，mysql
	DsDbmReport = "dbmReport"
	// DsDbmReportRaw 上报类数据，mysql_raw(非严格 schema)
	DsDbmReportRaw = "dbmReportRaw"
	// DsDbmStats 统计类数据，doris
	DsDbmStats = "dbmStats"
	// DsDbmStatsHttp 统计类数据，doris_http(stream load)。
	// 内置默认入库项都不用它，需要用 stream load 写入时在 data.xxx.yaml 里覆盖 datasource 到这里
	DsDbmStatsHttp = "dbmStatsHttp"
)

// builtinSinkers 内置的默认入库项，按注册顺序排列。
// 新增一个消费入库项，只需要在本文件 init() 里增加一条，所有环境升级二进制后自动生效，
// 启动时会据此生成 data.defaults.yaml。
var builtinSinkers []*SinkerConfig

// builtinSinkerIndex Key() -> 内置默认配置
var builtinSinkerIndex = make(map[string]*SinkerConfig)

// RegisterDefaultSinker 注册一个 strict_schema=true 的默认入库项，同时注册其 model。
// spec.ModelTable 为空时自动取 modelObj.TableName()。
func RegisterDefaultSinker(modelObj base.ModelSinker, spec SinkerConfig) {
	if err := sinker.RegisterModelSinker(modelObj); err != nil {
		panic(err)
	}
	if spec.ModelTable == "" {
		spec.ModelTable = modelObj.TableName()
	} else if spec.ModelTable != modelObj.TableName() {
		panic(fmt.Sprintf("builtin sinker model_table[%s] != model.TableName()[%s]",
			spec.ModelTable, modelObj.TableName()))
	}
	if spec.StrictSchema == nil {
		spec.StrictSchema = &cst.PtrTrue
	}
	addBuiltinSinker(spec)
}

// RegisterDefaultRawSinker 注册一个 strict_schema=false 的默认入库项。
// 不需要 model 代码，用 map[string]interface{} 反序列化后直接入库，
// 目标表结构需要提前在 datasource 侧创建好。
func RegisterDefaultRawSinker(spec SinkerConfig) {
	spec.StrictSchema = &cst.PtrFalse
	spec.SkipMigrateSchema = true
	addBuiltinSinker(spec)
}

func addBuiltinSinker(spec SinkerConfig) {
	if spec.ModelTable == "" {
		panic("builtin sinker model_table can not be empty")
	}
	if spec.Datasource == "" {
		panic(fmt.Sprintf("builtin sinker [%s] datasource can not be empty", spec.ModelTable))
	}
	if spec.WriteMode == "" {
		spec.WriteMode = cst.ModeReplace
	}
	if spec.Enable == nil {
		spec.Enable = &cst.PtrTrue
	}
	s := spec
	if _, ok := builtinSinkerIndex[s.Key()]; ok {
		panic(fmt.Sprintf("duplicate builtin sinker [%s]", s.Key()))
	}
	builtinSinkers = append(builtinSinkers, &s)
	builtinSinkerIndex[s.Key()] = &s
}

// initDefaultSinker 注册内置默认入库项。
// 不用 init() 而由 init.go 的 init() 显式调用，避免初始化顺序依赖文件名字母序
func initDefaultSinker() {
	RegisterDefaultSinker(&model.MysqlBackupResultModel{}, SinkerConfig{
		Topic:        "mysql_dbbackup_result",
		ModelTable:   "tb_mysql_backup_result",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.BinlogFileModel{}, SinkerConfig{
		Topic:        "mysql_binlog_result",
		ModelTable:   "tb_mysql_binlog_result",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.MysqlBackupStatusModel{}, SinkerConfig{
		Topic:        "mysql_dbbackup_progress",
		ModelTable:   "tb_mysql_backup_progress",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.MysqlPartitionResultModel{}, SinkerConfig{
		Topic:        "mysql_partition_result",
		ModelTable:   "tb_mysql_partition_result",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})

	RegisterDefaultRawSinker(SinkerConfig{
		Topic:             "sqlserver_dbbackup_result",
		ModelTable:        "tb_sqlserver_dbbackup_result",
		Datasource:        DsDbmReportRaw,
		WriteMode:         cst.ModeUpsert,
		StrictSchema:      &cst.PtrFalse,
		SkipMigrateSchema: cst.PtrTrue,
		OmitFields:        &([]string{}),
	})
	RegisterDefaultRawSinker(SinkerConfig{
		Topic:             "sqlserver_binlog_result",
		ModelTable:        "tb_sqlserver_binlog_result",
		Datasource:        DsDbmReportRaw,
		WriteMode:         cst.ModeUpsert,
		StrictSchema:      &cst.PtrFalse,
		SkipMigrateSchema: cst.PtrTrue,
		OmitFields:        &([]string{}),
	})

	RegisterDefaultSinker(&model.MysqlSlowLogModel{}, SinkerConfig{
		BkCollectorName: "mysql_slowlog",
		ModelTable:      "tb_mysql_slow_log",
		Datasource:      DsDbmStats,
		StrictSchema:    &cst.PtrTrue,
		FetchMinBytes:   1048576,
		IngestThreads:   1,
		SinkBatchSize:   10,
	})
	RegisterDefaultSinker(&model.MysqlTableSize{}, SinkerConfig{
		BkCollectorName: "mysql_db_table_size",
		ModelTable:      "mysql_db_table_size",
		Datasource:      DsDbmStats,
		StrictSchema:    &cst.PtrTrue,
		IngestThreads:   2,
		SinkBatchSize:   1000,
	})
	RegisterDefaultSinker(&model.MysqlProxyConnlog{}, SinkerConfig{
		BkCollectorName: "mysql_proxy_connlog_v2",
		ModelTable:      "mysql_proxy_connlog",
		Datasource:      DsDbmStats,
		StrictSchema:    &cst.PtrTrue,
		IngestThreads:   2,
		SinkBatchSize:   1000,
	})

	RegisterDefaultSinker(&model.RedisBackupResultModel{}, SinkerConfig{
		Topic:        "redis_backup_result",
		ModelTable:   "tb_redis_backup_result",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.RedisBinlogFileModel{}, SinkerConfig{
		Topic:        "redis_binlog_result",
		ModelTable:   "tb_redis_binlog_result",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.RedisBackupStatusModel{}, SinkerConfig{
		Topic:        "redis_backup_progress",
		ModelTable:   "tb_redis_backup_progress",
		Datasource:   DsDbmReport,
		StrictSchema: &cst.PtrTrue,
	})
	RegisterDefaultSinker(&model.DbmRetryEvent{}, SinkerConfig{
		BkCollectorName: "dbm_retry_event",
		ModelTable:      "dbm_retry_event",
		Datasource:      DsDbmReport, // dbm_retry_event 的 datasource 不重要
		StrictSchema:    &cst.PtrFalse,
	})
}
