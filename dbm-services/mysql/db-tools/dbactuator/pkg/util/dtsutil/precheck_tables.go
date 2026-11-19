/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dtsutil

import (
	"database/sql"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
)

// ResolveTablesForPrecheck 展开或解析表清单，并确认这些表在源端存在。
func ResolveTablesForPrecheck(db *sql.DB, scope *SyncScope, lockTables []TableItem) ([]LockedTable, error) {
	tables, err := ResolveTablesList(db, scope, lockTables)
	if err != nil {
		return nil, err
	}
	if err = VerifyBaseTablesExist(db, tables); err != nil {
		return nil, err
	}
	return tables, nil
}

// ResolveTablesList 解析待锁表清单。预检与 LockSourceTables 共用。
func ResolveTablesList(db *sql.DB, scope *SyncScope, lockTables []TableItem) ([]LockedTable, error) {
	if len(lockTables) > 0 {
		tables := make([]LockedTable, 0, len(lockTables))
		for _, it := range lockTables {
			schema := it.Schema
			if schema == "" {
				return nil, fmt.Errorf("lock_tables 项缺少 schema/db")
			}
			if it.Table == "" || it.Table == "*" {
				return nil, fmt.Errorf("lock_tables 仅支持具体表名，禁止通配")
			}
			tables = append(tables, LockedTable{Schema: schema, Table: it.Table})
		}
		logger.Info("lock_tables 待锁表数量 tables=%d", len(tables))
		return tables, nil
	}
	return ExpandSyncScope(db, scope)
}

// VerifyBaseTablesExist 确认每张表在 information_schema 中存在。
func VerifyBaseTablesExist(db *sql.DB, tables []LockedTable) error {
	if len(tables) == 0 {
		return fmt.Errorf("待锁表清单为空")
	}
	const q = `
SELECT 1
FROM information_schema.TABLES
WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ? AND TABLE_NAME = ?
LIMIT 1`
	for _, t := range tables {
		var one int
		err := db.QueryRow(q, t.Schema, t.Table).Scan(&one)
		if err == sql.ErrNoRows {
			return fmt.Errorf("表不存在: %s.%s", t.Schema, t.Table)
		}
		if err != nil {
			return fmt.Errorf("检查表存在失败 %s.%s: %w", t.Schema, t.Table, err)
		}
	}
	return nil
}
