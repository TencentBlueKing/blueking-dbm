/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"database/sql"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

const precheckStatusTimeoutSec = 30

// PreCheck 切换前预检：源连通 + 表可展开/存在 + Master 任务 status 可查。
// 不加锁、不 stop、不探测权限、不检查 blocking_ddls、不卡任务运行态。
// 多源按顺序 fail-fast。
func (c *Comp) PreCheck() error {
	if err := c.Init(); err != nil {
		return err
	}
	p := c.Params
	for _, ep := range p.SourceEndpoints {
		scope := ep.SyncScope
		if scope == nil || scope.IsEmpty() {
			scope = p.SyncScope
		}
		var useLockTables []TableItem
		if len(p.LockTables) > 0 {
			useLockTables = p.LockTables
		}
		if err := precheckOneSource(ep, scope, useLockTables); err != nil {
			return err
		}
	}

	resp, err := FetchTaskStatus(p.DtsMasterAddr, p.TaskName, precheckStatusTimeoutSec)
	if err != nil {
		return fmt.Errorf("预检查询任务 status 失败: %w", err)
	}
	if err = validateTaskStatusFetchable(resp); err != nil {
		return err
	}
	logger.Info("预检通过: sources=%d task=%s status_items=%d",
		len(p.SourceEndpoints), p.TaskName, len(resp.Data))
	return nil
}

func precheckOneSource(ep SourceEndpoint, scope *SyncScope, lockTables []TableItem) error {
	srcLabel := fmt.Sprintf("%s:%d", ep.Host, ep.Port)
	if ep.SourceName != "" {
		srcLabel = fmt.Sprintf("%s(%s)", srcLabel, ep.SourceName)
	}
	inst := native.InsObject{
		Host: ep.Host,
		Port: ep.Port,
		User: ep.User,
		Pwd:  ep.Password,
	}
	worker, err := inst.Conn()
	if err != nil {
		return fmt.Errorf("预检连接源端 %s 失败: %w", srcLabel, err)
	}
	defer worker.Close()

	tables, err := ResolveTablesForPrecheck(worker.Db, scope, lockTables)
	if err != nil {
		return fmt.Errorf("预检源端 %s 表清单失败: %w", srcLabel, err)
	}
	logger.Info("预检源端 %s 表清单就绪 tables=%d", srcLabel, len(tables))
	return nil
}

// ResolveTablesForPrecheck 展开或解析待锁表，并确认表在源端存在；不加锁。
func ResolveTablesForPrecheck(db *sql.DB, scope *SyncScope, lockTables []TableItem) ([]LockedTable, error) {
	tables, err := resolveTablesList(db, scope, lockTables)
	if err != nil {
		return nil, err
	}
	if err = VerifyBaseTablesExist(db, tables); err != nil {
		return nil, err
	}
	return tables, nil
}

// resolveTablesList 与 LockSourceTables 的清单解析语义对齐（不加锁）。
func resolveTablesList(db *sql.DB, scope *SyncScope, lockTables []TableItem) ([]LockedTable, error) {
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
		if len(tables) > SoftTableLimit {
			return nil, fmt.Errorf("lock_tables 数量 %d 超过软上限 %d", len(tables), SoftTableLimit)
		}
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

// validateTaskStatusFetchable 仅要求能查到任务 status（data 非空）；不卡运行态、不看 blocking_ddls。
func validateTaskStatusFetchable(resp *TaskStatusListResponse) error {
	if resp == nil {
		return fmt.Errorf("预检任务 status 响应为空")
	}
	if len(resp.Data) == 0 {
		return fmt.Errorf("预检任务 status 无数据（task 可能不存在）")
	}
	return nil
}
