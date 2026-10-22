/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package migrator

import (
	"strings"
	"testing"
)

func TestDataPrecheckRejectsDrift(t *testing.T) {
	cases := []struct {
		name   string
		mutate func(*Table)
	}{
		{name: "missing column", mutate: func(table *Table) { delete(table.Columns, "trigger_count") }},
		{name: "column type", mutate: func(table *Table) {
			column := table.Columns["priority"]
			column.DataType = "json"
			table.Columns["priority"] = column
		}},
		{name: "unique index", mutate: func(table *Table) {
			for i := range table.Indexes {
				if table.Indexes[i].Name == "idx_name" {
					table.Indexes[i].Unique = false
				}
			}
		}},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			store := schemaStore(t)
			item.mutate(store.snap.Tables[strategyTableName()])
			ddl := store.ddl
			if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
				t.Fatal("strategy drift should fail data precheck")
			}
			if store.snap.Tables["dbha_data_migrations"] != nil || len(store.snap.Data) != 0 || store.ddl != ddl {
				t.Fatal("failed data precheck wrote a ledger or ddl")
			}
		})
	}
}

func TestLoadSkipsInventoryScan(t *testing.T) {
	store := schemaStore(t)
	if store.inventoryLoads != 0 {
		t.Fatal("schema migration loaded inventory details")
	}
	store.snap.RowCounts[statusTable] = 4
	store.snap.Strategies = []StrategyState{{BkBizID: 1, Event: "custom"}}
	snap, err := store.Load()
	if err != nil || len(snap.RowCounts) != 0 || len(snap.Strategies) != 0 {
		t.Fatal("regular load included row counts or strategy rows")
	}
	inv, err := store.LoadInventory()
	if err != nil || inv.RowCounts[statusTable] != 4 || len(inv.Strategies) != 1 {
		t.Fatal("inventory load missed row counts or strategy rows")
	}
	ddl := store.ddl
	before := store.inventoryLoads
	if err = run(Options{Inventory: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.inventoryLoads <= before || store.ddl != ddl {
		t.Fatal("inventory did not load details, or it wrote ddl")
	}
}

func TestExistingRowsDoNotBackfill(t *testing.T) {
	store := schemaStore(t)
	store.snap.Strategies = []StrategyState{{
		BkBizID: 1, Event: "custom", Priority: 4, UpdatedAt: "custom",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.snap.Strategies) != 1 || len(store.snap.Data) != 0 || store.snap.Strategies[0].Priority != 4 {
		t.Fatal("existing data auto inserted or rewrote a row")
	}
	if !infoHas(recorded, "action: skip") {
		t.Fatal("missing default row did not log action: skip")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.snap.Strategies) != len(defaultStrategies())+1 || store.snap.Strategies[0].Priority != 4 {
		t.Fatal("repair-missing-data did not keep the existing row and insert the defaults")
	}
	if _, ok := store.snap.Data[dataVersion]; !ok {
		t.Fatal("completed default identities did not record the data ledger")
	}
}

func TestSoftDeletedStrategyIsNotRestored(t *testing.T) {
	store := schemaStore(t)
	event := defaultStrategies()[0].Event
	store.snap.Strategies = []StrategyState{{
		BkBizID: 0, Event: event, Priority: 3, UpdatedAt: "edited", Status: "deleted",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.snap.Strategies) != 1 || len(store.snap.Data) != 0 {
		t.Fatal("soft-deleted data was backfilled")
	}
	if !infoHas(recorded, "action: keep-deleted", event) {
		t.Fatal("soft-deleted row did not log action: keep-deleted")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	row := store.snap.Strategies[0]
	if row.Status != "deleted" || row.Priority != 3 || row.UpdatedAt != "edited" {
		t.Fatal("repair-missing-data restored a soft-deleted row")
	}
	if len(store.snap.Strategies) != len(defaultStrategies()) {
		t.Fatal("repair-missing-data did not insert the absent identities")
	}
}

func TestStrategyDeletedEitherMarker(t *testing.T) {
	if !strategyDeleted(strategyHit{Status: "deleted"}) || !strategyDeleted(strategyHit{Deleted: true}) {
		t.Fatal("soft-delete marker was ignored")
	}
	if strategyDeleted(strategyHit{Status: "enabled"}) {
		t.Fatal("active row was treated as deleted")
	}
}

func TestMissingDatabasePrivilege(t *testing.T) {
	schema := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	schema.snap.CanCreate = false
	err := run(Options{Type: MigrateTypeSchema}, []Store{schema})
	if err == nil || schema.snap.Database || !strings.Contains(err.Error(), "missing create privilege") {
		t.Fatal("schema on a missing database ignored the global create privilege")
	}
	data := newMem("127.0.0.1:3306", Identity{ServerUUID: "u2", Hostname: "db", Port: 3306})
	data.snap.CanCreate = true
	err = run(Options{Type: MigrateTypeData}, []Store{data})
	if err == nil || data.snap.Database || data.ddl != 0 || !strings.Contains(err.Error(), "strategy table is not ready") {
		t.Fatal("data on a missing database used create privilege or created the database")
	}
}

func TestExistingDatabaseRequiresWritePrivilege(t *testing.T) {
	store := schemaStore(t)
	store.snap.CanWrite = false
	store.snap.CanCreate = true
	err := run(Options{Type: MigrateTypeSchema}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "missing migrate privilege") {
		t.Fatal("existing database accepted a grant that cannot write it")
	}
}

func schemaStore(t *testing.T) *memStore {
	t.Helper()
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	return store
}

func infoHas(recorded *warnLog, parts ...string) bool {
	for _, line := range recorded.infos {
		matched := true
		for _, part := range parts {
			if !strings.Contains(line, part) {
				matched = false
				break
			}
		}
		if matched {
			return true
		}
	}
	return false
}
