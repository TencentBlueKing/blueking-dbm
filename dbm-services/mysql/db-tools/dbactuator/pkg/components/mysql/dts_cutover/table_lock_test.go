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
	"encoding/json"
	"strings"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
)

func TestBuildFlushTablesReadLockSQL(t *testing.T) {
	sql, err := BuildFlushTablesReadLockSQL([]LockedTable{
		{Schema: "app", Table: "t1"},
		{Schema: "app", Table: "t2"},
	})
	require.NoError(t, err)
	require.Equal(t, "FLUSH TABLES `app`.`t1`,`app`.`t2` WITH READ LOCK", sql)
	require.False(t, strings.Contains(sql, "FLUSH TABLES WITH READ LOCK"))
}

func TestBuildFlushTablesReadLockSQLRejectEmpty(t *testing.T) {
	_, err := BuildFlushTablesReadLockSQL(nil)
	require.Error(t, err)
}

func TestValidateFlushSQLBudget(t *testing.T) {
	sql := "FLUSH TABLES `app`.`t1` WITH READ LOCK"
	require.NoError(t, ValidateFlushSQLBudget(sql, 4*1024*1024))

	huge := "FLUSH TABLES " + strings.Repeat("`db`.`t`,", SoftTableLimit) + "`db`.`x` WITH READ LOCK"
	err := ValidateFlushSQLBudget(huge, PacketMarginBytes+10)
	require.Error(t, err)
}

func TestTableItemUnmarshal(t *testing.T) {
	var items []TableItem
	require.NoError(t, json.Unmarshal([]byte(`[{"db":"app","table":"t1"},"app.t2",{"schema":"s","table":"t3"}]`), &items))
	require.Equal(t, "app", items[0].Schema)
	require.Equal(t, "t1", items[0].Table)
	require.Equal(t, "app", items[1].Schema)
	require.Equal(t, "t2", items[1].Table)
	require.Equal(t, "s", items[2].Schema)
}

func TestSyncScopeIsEmpty(t *testing.T) {
	require.True(t, (*SyncScope)(nil).IsEmpty())
	require.True(t, (&SyncScope{}).IsEmpty())
	require.False(t, (&SyncScope{DoDBs: []string{"app"}}).IsEmpty())
	require.False(t, (&SyncScope{TableRoutes: []TableRoute{{SourceDB: "app", SourceTable: "t1"}}}).IsEmpty())
}

func TestTableRouteUnmarshalAndAccessors(t *testing.T) {
	var scope SyncScope
	raw := `{
		"table_routes": [
			{"source_db": "db_x", "source_table": "t1", "target_db": "db_y"},
			{"source_db_pattern": "shard_*", "source_table_pattern": "t_*", "source_name": "src1"}
		]
	}`
	require.NoError(t, json.Unmarshal([]byte(raw), &scope))
	require.Len(t, scope.TableRoutes, 2)
	require.Equal(t, "db_x", scope.TableRoutes[0].SourceSchema())
	require.Equal(t, "t1", scope.TableRoutes[0].SourceTableName())
	require.Equal(t, "db_y", scope.TableRoutes[0].TargetDB)
	require.Equal(t, "shard_*", scope.TableRoutes[1].SourceSchema())
	require.Equal(t, "t_*", scope.TableRoutes[1].SourceTableName())
	require.Equal(t, "src1", scope.TableRoutes[1].SourceName)
}

func TestGlobToSQLLike(t *testing.T) {
	// * → %；字面 _/% 转义，避免被 LIKE 当成元字符
	require.Equal(t, "shard\\_%", globToSQLLike("shard_*"))
	require.Equal(t, "a\\_b%", globToSQLLike("a_b*"))
	require.Equal(t, "shard\\_\\%", globToSQLLike("shard_%"))
}

func TestExpandSyncScopeTableRoutesExact(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	scope := &SyncScope{
		TableRoutes: []TableRoute{{SourceDB: "app", SourceTable: "t1"}},
	}
	tables, err := ExpandSyncScope(db, scope)
	require.NoError(t, err)
	require.Equal(t, []LockedTable{{Schema: "app", Table: "t1"}}, tables)
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestExpandSyncScopeTableRoutesOnlyStarTable(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	mock.ExpectQuery(`FROM information_schema\.TABLES`).
		WithArgs("app").
		WillReturnRows(sqlmock.NewRows([]string{"TABLE_SCHEMA", "TABLE_NAME"}).
			AddRow("app", "t1").
			AddRow("app", "t2"))

	scope := &SyncScope{
		TableRoutes: []TableRoute{{SourceDB: "app", SourceTable: "*"}},
	}
	tables, err := ExpandSyncScope(db, scope)
	require.NoError(t, err)
	require.Equal(t, []LockedTable{
		{Schema: "app", Table: "t1"},
		{Schema: "app", Table: "t2"},
	}, tables)
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestExpandSyncScopeTableRoutesRejectRegex(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	_, err = ExpandSyncScope(db, &SyncScope{
		TableRoutes: []TableRoute{{SourceDBPattern: "~^shard_", SourceTable: "*"}},
	})
	require.Error(t, err)
	require.Contains(t, err.Error(), "正则")
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestExpandSyncScopeTableRoutesRejectEmptyExpand(t *testing.T) {
	// 旧 bug：IsEmpty 因 table_routes 非空通过，但 Expand 忽略 routes → 空清单。
	// 现应能展开 exact route，不再因「忽略 routes」失败。
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()
	tables, err := ExpandSyncScope(db, &SyncScope{
		TableRoutes: []TableRoute{{SourceDB: "only_via_route", SourceTable: "t"}},
	})
	require.NoError(t, err)
	require.Len(t, tables, 1)
}

func TestBuildLockMasterSnapshots(t *testing.T) {
	snaps, err := BuildLockMasterSnapshots([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{MasterBinlog: "(binlog.000001, 100)"},
		},
	})
	require.NoError(t, err)
	require.Equal(t, "binlog.000001", snaps["src1"].File)
	require.Equal(t, int64(100), snaps["src1"].Position)
}

func TestCheckSnapshotCatchupBlockingDDL(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
				BlockingDDLs:        []string{"ALTER TABLE t"},
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
	require.Contains(t, err.Error(), "blocking_ddls")
}

func TestCheckSnapshotCatchupLiveMasterAheadOK(t *testing.T) {
	// 加锁快照=100；实时 master 因未迁移表前进到 200；syncer 已追到 100 → 通过
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.NoError(t, err)
}

func TestCheckSnapshotCatchupSyncerBehindRejected(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 90)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
	require.Contains(t, err.Error(), "未追上加锁快照")
}

func TestCheckSnapshotCatchupSBMRejected(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 1,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
}

func TestCheckSnapshotCatchupMultiSourceOneBehind(t *testing.T) {
	snap1, _ := ParseBinlogCoord("(binlog.000001, 100)")
	snap2, _ := ParseBinlogCoord("(binlog.000001, 50)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
		{
			SourceName: "src2",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 80)",
				SyncerBinlog:        "(binlog.000001, 40)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap1, "src2": snap2})
	require.Error(t, err)
	require.Contains(t, err.Error(), "src2")
}

func TestCheckSnapshotCatchupMissingSnapshot(t *testing.T) {
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 100)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{})
	require.Error(t, err)
}

func TestCheckSnapshotCatchupMissingStatusSource(t *testing.T) {
	// snapshots 有两源，本轮 status 只回一源且已追平 → 必须失败（禁止子集假成功）
	snap1, _ := ParseBinlogCoord("(binlog.000001, 100)")
	snap2, _ := ParseBinlogCoord("(binlog.000001, 50)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap1, "src2": snap2})
	require.Error(t, err)
	require.Contains(t, err.Error(), "src2")
	require.Contains(t, err.Error(), "未返回该源")
}
