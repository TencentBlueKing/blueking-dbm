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
			if store.snap.Tables[dataLedgerTable] != nil || len(store.snap.Data) != 0 || store.ddl != ddl {
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
	snap, err := store.Load()
	if err != nil || len(snap.RowCounts) != 0 {
		t.Fatal("regular load included row counts")
	}
	inv, err := store.LoadInventory()
	if err != nil || inv.RowCounts[statusTable] != 4 {
		t.Fatal("inventory load missed row counts")
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
	store.strategies = []StrategyState{{
		BkBizID: 1, Event: "custom", Priority: 4, UpdatedAt: "custom",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != 1 || len(store.snap.Data) != 0 || store.strategies[0].Priority != 4 {
		t.Fatal("existing data auto inserted or rewrote a row")
	}
	if !infoHas(recorded, "action: skip") {
		t.Fatal("missing default row did not log action: skip")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != len(defaultStrategies())+1 || store.strategies[0].Priority != 4 {
		t.Fatal("repair-missing-data did not keep the existing row and insert the defaults")
	}
	if _, ok := store.snap.Data[dataVersion]; !ok {
		t.Fatal("completed default identities did not record the data ledger")
	}
}

func TestSoftDeletedStrategyIsNotRestored(t *testing.T) {
	store := schemaStore(t)
	event := defaultStrategies()[0].TriggerEventName.String()
	store.strategies = []StrategyState{{
		BkBizID: 0, Event: event, Priority: 3, UpdatedAt: "edited", Status: "deleted",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != 1 || len(store.snap.Data) != 0 {
		t.Fatal("soft-deleted data was backfilled")
	}
	if !infoHas(recorded, "action: keep-deleted", event) {
		t.Fatal("soft-deleted row did not log action: keep-deleted")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	row := store.strategies[0]
	if row.Status != "deleted" || row.Priority != 3 || row.UpdatedAt != "edited" {
		t.Fatal("repair-missing-data restored a soft-deleted row")
	}
	if len(store.strategies) != len(defaultStrategies()) {
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

func TestStrategyHitPrefersSeedReasonThenLiveRow(t *testing.T) {
	seed := defaultStrategies()[0]
	event, reason := seed.TriggerEventName.String(), int(seed.TriggerEventNameReason)
	own := StrategyState{BkBizID: seed.BkBizID, Event: event, Reason: reason, Status: "enabled"}
	other := StrategyState{BkBizID: seed.BkBizID, Event: event, Reason: reason + 100, Status: "deleted"}
	for _, rows := range [][]StrategyState{{own, other}, {other, own}} {
		hit := strategyHits(rows)[seedIdentity(seed)]
		if !hit.Found || strategyDeleted(hit) {
			t.Fatal("hit depended on row order instead of the seed reason")
		}
	}

	ownDeleted := own
	ownDeleted.Status = "deleted"
	for _, rows := range [][]StrategyState{{ownDeleted, other}, {other, ownDeleted}} {
		if hit := strategyHits(rows)[seedIdentity(seed)]; !strategyDeleted(hit) {
			t.Fatal("soft-deleted seed row lost to another reason")
		}
	}

	live := other
	live.Status = "enabled"
	for _, rows := range [][]StrategyState{{live, other}, {other, live}} {
		if hit := strategyHits(rows)[seedIdentity(seed)]; strategyDeleted(hit) {
			t.Fatal("live row lost to a deleted row of the same rank")
		}
	}
}

// A NULL reason ranks below any other reason, as NULL sorts last in MySQL descending order.
// A live NULL-reason row must not win over a deleted row whose reason is merely different.
func TestStrategyHitNullReasonRanksLast(t *testing.T) {
	seed := defaultStrategies()[0]
	event, reason := seed.TriggerEventName.String(), int(seed.TriggerEventNameReason)
	nullLive := StrategyState{BkBizID: seed.BkBizID, Event: event, ReasonNull: true, Status: "enabled"}
	otherDeleted := StrategyState{BkBizID: seed.BkBizID, Event: event, Reason: reason + 100, Status: "deleted"}
	for _, rows := range [][]StrategyState{{nullLive, otherDeleted}, {otherDeleted, nullLive}} {
		if hit := strategyHits(rows)[seedIdentity(seed)]; !strategyDeleted(hit) {
			t.Fatal("null-reason row outranked a row with another reason")
		}
	}

	nullDeleted := nullLive
	nullDeleted.Status = "deleted"
	for _, rows := range [][]StrategyState{{nullLive, nullDeleted}, {nullDeleted, nullLive}} {
		if hit := strategyHits(rows)[seedIdentity(seed)]; strategyDeleted(hit) {
			t.Fatal("live null-reason row lost to a deleted null-reason row")
		}
	}
}

func TestStrategyHitRankOrder(t *testing.T) {
	const reason = 7
	order := []strategyRow{
		{Reason: reason, ReasonValid: true},
		{Reason: reason, ReasonValid: true, Deleted: true},
		{Reason: reason + 1, ReasonValid: true},
		{Reason: reason + 1, ReasonValid: true, Status: "deleted"},
		{ReasonValid: false},
		{ReasonValid: false, Deleted: true},
	}
	for i := 1; i < len(order); i++ {
		if strategyHitRank(order[i-1], reason) <= strategyHitRank(order[i], reason) {
			t.Fatalf("rank order broken, position: %d", i)
		}
	}
	if hit := bestStrategyHit(nil, reason); hit.Found {
		t.Fatal("no rows must mean not found")
	}
}

func TestDataOnMissingDatabase(t *testing.T) {
	data := newMem("127.0.0.1:3306", Identity{ServerUUID: "u2", Hostname: "db", Port: 3306})
	err := run(Options{Type: MigrateTypeData}, []Store{data})
	if err == nil || data.snap.Database || data.ddl != 0 ||
		!strings.Contains(err.Error(), "strategy table is not ready") {
		t.Fatal("data on a missing database created the database")
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
