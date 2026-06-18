// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ibdstatistic

import (
	"fmt"
	"log/slog"

	"github.com/pkg/errors"
)

const (
	tableSchemaQuery = `
		SELECT
		    TABLE_SCHEMA,
		    TABLE_NAME,
		    ifnull(ENGINE, 'NONE') as ENGINE,
		    ifnull(TABLE_ROWS, '0') as TABLE_ROWS,
		    ifnull(DATA_LENGTH, '0') as DATA_LENGTH,
		    ifnull(INDEX_LENGTH, '0') as INDEX_LENGTH,
		    ifnull(DATA_FREE, '0') as DATA_FREE
		  FROM information_schema.tables
		  WHERE TABLE_TYPE='BASE TABLE' AND ENGINE='ROCKSDB' AND TABLE_SCHEMA = '%s' 
		`
	dbListQuery = `
		SELECT
		    SCHEMA_NAME
		  FROM information_schema.schemata
		  WHERE SCHEMA_NAME NOT IN ('mysql', 'performance_schema', 'information_schema', 'sys', 'infodba_schema')
		`
)

// collectRocksdb 通过查询 information_schema 获取 rocksdb 引擎的表大小
// rocksdb 引擎的表大小无法从文件系统直接获取，需要按 TABLE_SCHEMA 遍历避免一次查询全部 tables 带来的开销
// rocksdb 引擎更准确的统计是查询: ROCKSDB_INDEX_FILE_MAP,ROCKSDB_SST_PROPS,ROCKSDB_DDL。这里不用做到那么精细
// 在 slave 上运行
func (c *ibdStatistic) collectRocksdb() (map[string]int64, map[string]int64, error) {
	type SchemaInfo struct {
		SchemaName string `db:"SCHEMA_NAME"`
	}
	type RocksdbTableInfo struct {
		TableSchema string `db:"TABLE_SCHEMA"`
		TableName   string `db:"TABLE_NAME"`
		Engine      string `db:"ENGINE"`
		DataLength  int64  `db:"DATA_LENGTH"`
		IndexLength int64  `db:"INDEX_LENGTH"`
		TableRows   int64  `db:"TABLE_ROWS"`
		DataFree    int64  `db:"DATA_FREE"`
	}

	// 获取所有非系统库
	var schemas []*SchemaInfo
	slog.Info("ibd-statistic collect rocksdb", slog.String("sql", dbListQuery))
	if err := c.db.Select(&schemas, dbListQuery); err != nil {
		slog.Error("ibd-statistic collect rocksdb", slog.String("error", err.Error()))
		return nil, nil, errors.WithMessage(err, "get schema list from information_schema.schemata")
	}

	var err error
	dbSize := make(map[string]int64)
	tableSize := make(map[string]int64)

	// 按 TABLE_SCHEMA 遍历，避免一次查询全部 tables 带来的开销
	for _, schema := range schemas {
		var tables []*RocksdbTableInfo
		query := fmt.Sprintf(tableSchemaQuery, schema.SchemaName)
		if err := c.db.Select(&tables, query); err != nil {
			slog.Error("ibd-statistic collect rocksdb",
				slog.String("schema", schema.SchemaName),
				slog.String("error", err.Error()),
				slog.String("sql", query))
			continue
		}

		for _, info := range tables {
			dbName := info.TableSchema
			tableName := info.TableName

			dbName, tableName, err = c.rewriteMergeTableName(dbName, tableName)
			if err != nil {
				slog.Error("ibd-statistic collect rocksdb", slog.String("error", err.Error()))
			}
			dbTableName := fmt.Sprintf("%s.%s", dbName, tableName)

			size := info.DataLength + info.IndexLength
			if _, ok := dbSize[dbName]; !ok {
				dbSize[dbName] = 0
			}
			if _, ok := tableSize[dbTableName]; !ok {
				tableSize[dbTableName] = 0
			}
			dbSize[dbName] += size
			tableSize[dbTableName] += size
		}
	}
	return tableSize, dbSize, nil
}
