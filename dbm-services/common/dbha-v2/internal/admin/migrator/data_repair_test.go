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
	"fmt"
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
	seed := defaultStrategies()[0]
	event := seed.TriggerEventName.String()
	store.strategies = []StrategyState{{
		BkBizID: 0, Event: event, Reason: int(seed.TriggerEventNameReason), Priority: 3, UpdatedAt: "edited",
		Status: "deleted",
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

// The switch flow matches by event only, so a row of the same event covers the default whatever its reason.
func TestStrategyHitMatchesAnyReason(t *testing.T) {
	seed := defaultStrategies()[1]
	event, reason := seed.TriggerEventName.String(), int(seed.TriggerEventNameReason)
	own := StrategyState{BkBizID: seed.BkBizID, Event: event, Reason: reason, Status: "enabled"}
	other := StrategyState{BkBizID: seed.BkBizID, Event: event, Reason: reason + 100, Status: "enabled"}
	if hit := strategyHits([]StrategyState{other})[seedIdentity(seed)]; !hit.Found || strategyDeleted(hit) {
		t.Fatal("a live row with another reason did not hit the default strategy")
	}

	ownDeleted := own
	ownDeleted.Status = "deleted"
	for _, rows := range [][]StrategyState{{ownDeleted, other}, {other, ownDeleted}} {
		if hit := strategyHits(rows)[seedIdentity(seed)]; !hit.Found || strategyDeleted(hit) {
			t.Fatal("a soft-deleted row ranked above a live row of the same event")
		}
	}
}

func TestStrategyHitMatchesNullReason(t *testing.T) {
	seed := defaultStrategies()[0]
	nullLive := StrategyState{
		BkBizID: seed.BkBizID, Event: seed.TriggerEventName.String(), ReasonNull: true, Status: "enabled",
	}
	if hit := strategyHits([]StrategyState{nullLive})[seedIdentity(seed)]; !hit.Found {
		t.Fatal("a null-reason row of the same event did not hit the default strategy")
	}
}

func TestStrategyHitRankOrder(t *testing.T) {
	order := []strategyRow{
		{Status: "enabled"},
		{Deleted: true},
	}
	if strategyHitRank(order[0]) <= strategyHitRank(order[1]) {
		t.Fatal("live row did not rank above a soft-deleted row")
	}
	if strategyHitRank(strategyRow{Status: "deleted"}) != strategyHitRank(strategyRow{Deleted: true}) {
		t.Fatal("soft-delete markers ranked differently")
	}
	if hit := bestStrategyHit(nil); hit.Found {
		t.Fatal("no rows must mean not found")
	}
}

func TestDefaultStrategyIdentityUnique(t *testing.T) {
	seen := map[string]bool{}
	for _, seed := range defaultStrategies() {
		id := seedIdentity(seed)
		if seen[id] {
			t.Fatalf("default strategy identity repeated, trigger_event_name: %s", seed.TriggerEventName)
		}
		seen[id] = true
	}
}

// Default strategies must not collide with each other on any unique index of the model.
func TestDefaultStrategiesUniquePerIndex(t *testing.T) {
	seen := map[string]bool{}
	for _, seed := range defaultStrategies() {
		lookups, err := strategyLookups(seed)
		if err != nil {
			t.Fatal(err)
		}
		for _, lookup := range lookups {
			key := lookup.Index + fmt.Sprint(lookup.Values)
			if seen[key] {
				t.Fatalf("default strategies share a unique key, index: %s", lookup.Index)
			}
			seen[key] = true
		}
	}
}

// Every column of every unique index must map to a model value, so a new index cannot skip the check.
func TestStrategyLookupsCoverUniqueIndexes(t *testing.T) {
	spec, _ := tableByName(strategyTableName())
	unique := 0
	for _, index := range spec.Indexes {
		if index.Unique {
			unique++
		}
	}
	lookups, err := strategyLookups(defaultStrategies()[0])
	if err != nil {
		t.Fatal(err)
	}
	if unique == 0 || len(lookups) != unique {
		t.Fatalf("unique index lookups, want: %d, got: %d", unique, len(lookups))
	}
	for _, lookup := range lookups {
		index, _ := findIndexSpec(spec, lookup.Index)
		if len(lookup.Values) != len(index.Columns) {
			t.Fatalf("unique index lookup misses columns, index: %s", lookup.Index)
		}
	}
	values, err := modelColumnValues(defaultStrategies()[0])
	if err != nil {
		t.Fatal(err)
	}
	extended := spec
	extended.Indexes = append(append([]indexSpec{}, spec.Indexes...), indexSpec{
		Name: "idx_missing", Unique: true, Columns: []string{"missing"},
	})
	if _, err = strategyLookupsFrom(extended, values); err == nil {
		t.Fatal("a unique index column without a model value was accepted")
	}
}

// A user strategy of a default event keeps repair from adding a second strategy for that event.
func TestOtherReasonCoversDefault(t *testing.T) {
	store := schemaStore(t)
	seed := defaultStrategies()[1]
	event := seed.TriggerEventName.String()
	store.strategies = []StrategyState{{
		Name: "custom", BkBizID: seed.BkBizID, Event: event,
		Reason: int(seed.TriggerEventNameReason) + 100, Priority: 4, Status: "enabled",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != 1 || len(store.snap.Data) != 0 {
		t.Fatal("data migrate without repair inserted rows or recorded the data ledger")
	}
	if infoHas(recorded, "action: skip", "trigger_event_name: "+event+",") {
		t.Fatal("covered default strategy was logged as skip")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != len(defaultStrategies()) || eventRows(store, event) != 1 {
		t.Fatal("repair-missing-data added a second strategy for a covered event")
	}
	if store.strategies[0].Priority != 4 || store.strategies[0].Name != "custom" {
		t.Fatal("repair-missing-data rewrote the covering row")
	}
	if _, ok := store.snap.Data[dataVersion]; !ok {
		t.Fatal("covered default identities did not record the data ledger")
	}
}

// A default row whose reason changed still covers its event: repair neither fails nor warns.
func TestSameNameOtherReasonIsHit(t *testing.T) {
	for _, status := range []string{"enabled", "deleted"} {
		t.Run(status, func(t *testing.T) {
			store := schemaStore(t)
			seed := defaultStrategies()[1]
			store.strategies = []StrategyState{{
				Name: seed.Name, BkBizID: seed.BkBizID, Event: seed.TriggerEventName.String(),
				Reason: int(seed.TriggerEventNameReason) + 100, Priority: 4, Status: status,
			}}
			recorded := captureWarn(t)
			if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
				t.Fatal(err)
			}
			if len(store.strategies) != len(defaultStrategies()) || len(recorded.warnings) != 0 {
				t.Fatalf("reason drift was not a hit, warnings: %v", recorded.warnings)
			}
			if store.strategies[0].Reason != int(seed.TriggerEventNameReason)+100 {
				t.Fatal("repair-missing-data rewrote the reason")
			}
		})
	}
}

// A default row moved to another event keeps its name: only that default is skipped, the rest are repaired.
func TestRenamedEventConflictSkips(t *testing.T) {
	cases := []struct {
		name    string
		row     StrategyState
		deleted bool
	}{
		{name: "enabled", row: StrategyState{Status: "enabled"}},
		{name: "status deleted", row: StrategyState{Status: "deleted"}, deleted: true},
		{name: "deleted_at", row: StrategyState{Status: "enabled", Deleted: true}, deleted: true},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			store := schemaStore(t)
			seed := defaultStrategies()[1]
			row := item.row
			row.Name, row.BkBizID, row.Event, row.Priority = seed.Name, seed.BkBizID, "custom_event", 4
			row.Reason = int(seed.TriggerEventNameReason)
			store.strategies = []StrategyState{row}
			recorded := captureWarn(t)
			if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
				t.Fatal(err)
			}
			assertConflictSkipped(t, store, recorded, seed.TriggerEventName.String())
			guidance := "rename the conflicting row"
			if item.deleted {
				guidance = "in the database"
			}
			if !warnHas(recorded, "conflict_deleted: "+fmt.Sprint(item.deleted), guidance) {
				t.Fatalf("conflict guidance, warnings: %v", recorded.warnings)
			}

			before := len(store.strategies)
			if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
				t.Fatal(err)
			}
			if len(store.strategies) != before {
				t.Fatal("second repair changed the strategy rows")
			}
		})
	}
}

func TestConflictSkipLogsNullReason(t *testing.T) {
	store := schemaStore(t)
	seed := defaultStrategies()[0]
	store.strategies = []StrategyState{{
		Name: seed.Name, BkBizID: seed.BkBizID, Event: "custom_event", ReasonNull: true, Status: "enabled",
	}}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !warnHas(recorded, "conflict_reason: NULL", "conflict_name: "+seed.Name) {
		t.Fatalf("null conflict reason was not logged as NULL, warnings: %v", recorded.warnings)
	}
}

func TestRepairInsertsSkippedDefaultAfterRename(t *testing.T) {
	store := schemaStore(t)
	seed := defaultStrategies()[1]
	store.strategies = []StrategyState{{
		Name: seed.Name, BkBizID: seed.BkBizID, Event: "custom_event", Status: "enabled",
	}}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	store.strategies[0].Name = "custom"
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if eventRows(store, seed.TriggerEventName.String()) != 1 || len(store.snap.Data) != 1 {
		t.Fatal("repair did not insert the default once the conflict was cleared")
	}
	if !infoHas(recorded, "data_repaired: 1", "data_skipped: 0") {
		t.Fatalf("repair summary, infos: %v", recorded.infos)
	}
}

func TestConflictSkipDoesNotStopOtherEndpoint(t *testing.T) {
	left := schemaStore(t)
	seed := defaultStrategies()[1]
	left.strategies = []StrategyState{{
		Name: seed.Name, BkBizID: seed.BkBizID, Event: "custom_event", Status: "enabled",
	}}
	right := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db-b", Port: 3307})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{right}); err != nil {
		t.Fatal(err)
	}
	err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{left, right})
	if err != nil {
		t.Fatal(err)
	}
	if len(left.strategies) != len(defaultStrategies()) || len(right.strategies) != len(defaultStrategies()) {
		t.Fatal("a conflict on one endpoint changed what the other endpoint received")
	}
	if len(left.snap.Data) != 1 || len(right.snap.Data) != 1 {
		t.Fatal("an endpoint did not record the data ledger")
	}
}

func TestConflictSkipKeepsLedgerNameConflict(t *testing.T) {
	store := schemaStore(t)
	seed := defaultStrategies()[1]
	store.strategies = []StrategyState{{
		Name: seed.Name, BkBizID: seed.BkBizID, Event: "custom_event", Status: "enabled",
	}}
	store.snap.Data[dataVersion] = Ledger{Version: dataVersion, Name: "other_ledger"}
	err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store})
	assertErrorFields(t, err, "data ledger name conflict")
	if len(store.strategies) != 1 || store.snap.Data[dataVersion].Name != "other_ledger" {
		t.Fatal("conflicting data ledger inserted strategies or was rewritten")
	}
}

func assertConflictSkipped(t *testing.T, store *memStore, recorded *warnLog, event string) {
	t.Helper()
	if len(store.strategies) != len(defaultStrategies()) || eventRows(store, event) != 0 {
		t.Fatal("conflict-skip inserted the conflicting default or missed the others")
	}
	if _, ok := store.snap.Data[dataVersion]; !ok {
		t.Fatal("conflict-skip stopped the data ledger")
	}
	if !infoHas(recorded, "action: conflict-skip", "trigger_event_name: "+event+",") {
		t.Fatalf("conflict-skip action, infos: %v", recorded.infos)
	}
	if !infoHas(recorded, "data_repaired: 4", "data_skipped: 1") {
		t.Fatalf("conflict-skip summary, infos: %v", recorded.infos)
	}
	if !warnHas(recorded, "default strategy skipped by unique conflict", "index: idx_name",
		"conflict_event: custom_event") {
		t.Fatalf("conflict-skip warning, warnings: %v", recorded.warnings)
	}
}

func eventRows(store *memStore, event string) int {
	count := 0
	for _, row := range store.strategies {
		if row.Event == event {
			count++
		}
	}
	return count
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
