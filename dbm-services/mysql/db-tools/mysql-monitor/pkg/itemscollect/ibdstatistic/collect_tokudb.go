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

func (c *ibdStatistic) collectTokudb() (map[string]int64, map[string]int64, error) {
	type TokudbInfo struct {
		TableSchema string `db:"table_schema"`
		TableName   string `db:"table_name"`
		Size        int64  `db:"bt_size_allocated"`
	}
	var res []*TokudbInfo
	query := "SELECT table_schema,table_name,bt_size_allocated FROM information_schema.TokuDB_fractal_tree_info"
	slog.Info("ibd-statistic collect tokudb", slog.String("sql", query))

	if err := c.db.Select(&res, query); err != nil {
		slog.Error("ibd-statistic collect tokudb", slog.String("error", err.Error()))
		return nil, nil, errors.WithMessage(err, "get tokudb info from TokuDB_fractal_tree_info")
	}

	var err error
	dbSize := make(map[string]int64)
	tableSize := make(map[string]int64)
	for _, info := range res {
		dbName := info.TableSchema
		tableName := info.TableName

		dbName, tableName, err = c.rewriteMergeTableName(dbName, tableName)
		if err != nil {
			slog.Error("ibd-statistic collect tokudb", slog.String("error", err.Error()))
			//return nil, nil, err
		}
		dbTableName := fmt.Sprintf("%s.%s", dbName, tableName)

		if _, ok := dbSize[dbName]; !ok {
			dbSize[dbName] = 0
		}
		if _, ok := tableSize[dbTableName]; !ok {
			tableSize[dbTableName] = 0
		}
		dbSize[dbName] += info.Size
		tableSize[dbTableName] += info.Size
	}
	return tableSize, dbSize, nil
}
