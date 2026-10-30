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
	"bytes"
	"errors"
	"strings"
	"testing"
)

func TestRecordedIndexLossNeedsRepair(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	step := findStep(objectIndex, "t_db_switching_log", "", "idx_level")
	if step.Version == 0 {
		t.Fatal("catalog has no idx_level step")
	}
	table := store.snap.Tables[step.Table]
	table.Indexes = dropNamedIndex(table.Indexes, step.Index)
	ddl := store.ddl

	err := run(Options{Type: MigrateTypeSchema}, []Store{store})
	assertErrorFields(t, err, "name: "+step.Name, "result: drift")
	if store.ddl != ddl || hasIndex(store.snap.Tables[step.Table], step.Index) {
		t.Fatal("recorded index drift wrote ddl")
	}

	if err = run(Options{Type: MigrateTypeSchema, RepairMissing: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !hasIndex(store.snap.Tables[step.Table], step.Index) {
		t.Fatal("repair-missing did not rebuild the index")
	}
	if store.ddl != ddl+1 || store.applied[len(store.applied)-1] != step.Apply {
		t.Fatalf("repair-missing ran more than the index, before: %d, after: %d", ddl, store.ddl)
	}

	repaired := store.ddl
	if err = run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != repaired {
		t.Fatal("second run changed the repaired index")
	}
}

func TestInventoryIgnoresMigrateType(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	var output bytes.Buffer
	if err := run(Options{Inventory: true, Type: "strategy", Report: &output}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != 0 || store.snap.Database || !strings.Contains(output.String(), "result: ok") {
		t.Fatalf("inventory with a migrate type wrote or failed, report: %s", output.String())
	}
}

func TestAllWithRepairsRestoresSchemaOnly(t *testing.T) {
	for _, item := range []struct {
		opts       Options
		strategies int
	}{
		{Options{Type: MigrateTypeAll, RepairMissingSchema: true}, 1},
		{Options{Type: MigrateTypeAll, RepairMissing: true}, len(defaultStrategies())},
	} {
		store := migrated("127.0.0.1:3306", "u1")
		delete(store.snap.Tables[statusTable].Columns, "probe")
		delete(store.snap.Tables, "t_db_switching_log")
		store.strategies = store.strategies[:1]

		if err := run(item.opts, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if _, ok := store.snap.Tables[statusTable].Columns["probe"]; !ok {
			t.Fatalf("schema repair did not restore the column, repair_missing: %t", item.opts.RepairMissing)
		}
		if store.snap.Tables["t_db_switching_log"] == nil {
			t.Fatalf("schema repair did not rebuild the table, repair_missing: %t", item.opts.RepairMissing)
		}
		if len(store.strategies) != item.strategies {
			t.Fatalf("strategy count, repair_missing: %t, count: %d", item.opts.RepairMissing, len(store.strategies))
		}

		repaired := store.ddl
		if err := run(item.opts, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if store.ddl != repaired {
			t.Fatal("second repair run executed ddl")
		}
	}
}

func TestRepairMissingFollowsType(t *testing.T) {
	schema := migrated("127.0.0.1:3306", "u1")
	delete(schema.snap.Tables[statusTable].Columns, "probe")
	delete(schema.snap.Tables, "t_db_switching_log")
	step := findStep(objectIndex, strategyTableName(), "", "idx_created_at")
	strategy := schema.snap.Tables[strategyTableName()]
	strategy.Indexes = dropNamedIndex(strategy.Indexes, step.Index)
	schema.strategies = schema.strategies[:1]

	if err := run(Options{Type: MigrateTypeSchema, RepairMissing: true}, []Store{schema}); err != nil {
		t.Fatal(err)
	}
	if _, ok := schema.snap.Tables[statusTable].Columns["probe"]; !ok {
		t.Fatal("schema repair-missing did not restore the column")
	}
	if schema.snap.Tables["t_db_switching_log"] == nil || !hasIndex(strategy, step.Index) {
		t.Fatal("schema repair-missing did not rebuild the table or index")
	}
	if len(schema.strategies) != 1 {
		t.Fatal("schema repair-missing inserted strategies")
	}

	data := migrated("127.0.0.1:3307", "u2")
	data.strategies = data.strategies[:1]
	ddl := data.ddl
	if err := run(Options{Type: MigrateTypeData, RepairMissing: true}, []Store{data}); err != nil {
		t.Fatal(err)
	}
	if len(data.strategies) != len(defaultStrategies()) {
		t.Fatalf("data repair-missing did not insert strategies, count: %d", len(data.strategies))
	}
	if data.ddl != ddl {
		t.Fatal("data repair-missing executed ddl")
	}
}

func TestSameNameIndexShapeConflicts(t *testing.T) {
	step := findStep(objectIndex, strategyTableName(), "", "idx_description")
	shapes := []Index{
		{Name: step.Index, Columns: []string{"description"}, Prefix: []int{10}},
		{Name: step.Index, Columns: []string{"created_at"}},
		{Name: strings.ToUpper(step.Index), Columns: []string{"description"}, Prefix: []int{10}},
	}
	for _, shape := range shapes {
		for _, opts := range []Options{
			{Type: MigrateTypeSchema},
			{Type: MigrateTypeSchema, RepairMissingSchema: true},
		} {
			store := migrated("127.0.0.1:3306", "u1")
			table := store.snap.Tables[step.Table]
			table.Indexes = append(dropNamedIndex(table.Indexes, step.Index), shape)
			ddl := store.ddl

			err := run(opts, []Store{store})
			assertErrorFields(t, err, "name: "+step.Name, "result: conflict")
			if store.ddl != ddl {
				t.Fatalf("same-name index conflict wrote ddl, index: %s", shape.Name)
			}
		}

		store := migrated("127.0.0.1:3306", "u1")
		table := store.snap.Tables[step.Table]
		table.Indexes = append(dropNamedIndex(table.Indexes, step.Index), shape)
		var output bytes.Buffer
		err := run(Options{Inventory: true, Report: &output}, []Store{store})
		assertErrorFields(t, err, "structural conflict")
		report := output.String()
		if !strings.Contains(report, "class: conflict") || !strings.Contains(report, "object: "+step.Index) {
			t.Fatalf("inventory did not report the index conflict, index: %s, report: %s", shape.Name, report)
		}
	}
}

func TestRebuiltStrategyTableNeedsDataRepair(t *testing.T) {
	for _, item := range []struct {
		opts       Options
		strategies int
	}{
		{Options{Type: MigrateTypeAll, RepairMissingSchema: true}, 0},
		{Options{Type: MigrateTypeAll, RepairMissing: true}, len(defaultStrategies())},
	} {
		store := migrated("127.0.0.1:3306", "u1")
		delete(store.snap.Tables, strategyTableName())
		store.strategies = nil

		if err := run(item.opts, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if store.snap.Tables[strategyTableName()] == nil {
			t.Fatalf("strategy table was not rebuilt, repair_missing: %t", item.opts.RepairMissing)
		}
		if len(store.strategies) != item.strategies {
			t.Fatalf("strategy count, repair_missing: %t, count: %d", item.opts.RepairMissing, len(store.strategies))
		}
	}
}

func TestRepairSchemaCreatesPartialTables(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	store.snap.Tables[statusTable] = tableFromSpec(statusSpec())
	store.snap.Tables[strategyTableName()] = withIndexes(strategySpec())
	opts := Options{Type: MigrateTypeAll, RepairMissingSchema: true}

	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	for _, spec := range modelTables() {
		if store.snap.Tables[spec.Name] == nil {
			t.Fatalf("missing table was not created, table: %s", spec.Name)
		}
	}
	if len(store.strategies) != len(defaultStrategies()) {
		t.Fatalf("empty strategy table was not initialized, count: %d", len(store.strategies))
	}

	ddl := store.ddl
	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != ddl {
		t.Fatal("second run executed ddl")
	}
}

func TestEmptyServerUUIDStopsBeforeLock(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	right := newTrackedStore("right", Identity{Hostname: "db", Port: 3306}, &calls)

	err := run(Options{Type: MigrateTypeSchema}, []Store{left, right})
	assertErrorFields(t, err, "server identity unavailable", "endpoint: right")
	assertCalls(t, calls, "identity:left", "identity:right", "unlock:right", "unlock:left")
	assertUnlocks(t, left, right)
	if left.ddl != 0 || right.ddl != 0 {
		t.Fatal("identity failure wrote ddl")
	}
}

func TestPrecheckFailureWritesNothing(t *testing.T) {
	cause := errors.New("probe failed")
	cases := []struct {
		name   string
		want   string
		mutate func(*trackedStore)
	}{
		{name: "super read only", want: "server is read only", mutate: func(s *trackedStore) {
			s.snap.SuperReadOnly = true
		}},
		{name: "version unavailable", want: "database version unavailable", mutate: func(s *trackedStore) {
			s.snap.VersionOK = false
		}},
		{name: "schema ledger shape", want: "migration ledger conflict", mutate: func(s *trackedStore) {
			s.snap.LedgerSchemaOK = false
		}},
		{name: "data ledger shape", want: "migration ledger conflict", mutate: func(s *trackedStore) {
			s.snap.LedgerDataOK = false
		}},
		{name: "load", want: cause.Error(), mutate: func(s *trackedStore) { s.loadErr = cause }},
		{name: "probe facts", want: cause.Error(), mutate: func(s *trackedStore) { s.probeErr = cause }},
		{name: "table non empty", want: cause.Error(), mutate: func(s *trackedStore) { s.nonEmptyErr = cause }},
		{name: "duplicate probe", want: cause.Error(), mutate: func(s *trackedStore) {
			table := s.snap.Tables[strategyTableName()]
			table.Indexes = dropNamedIndex(table.Indexes, "idx_biz_event_reason")
			s.duplicateErr = cause
		}},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			left := newTrackedStore("left", testIdentity("u1"), &[]string{})
			right := migratedTracked(t, "right", "u2")
			item.mutate(right)
			ddl, ledgers := right.ddl, len(right.snap.Schema)

			err := run(Options{Type: MigrateTypeSchema}, []Store{left, right})
			assertErrorFields(t, err, "precheck failed, endpoint: right", item.want)
			if item.want == cause.Error() && !errors.Is(err, cause) {
				t.Fatalf("precheck error lost its cause, errmsg: %s", err)
			}
			if left.ddl != 0 || right.ddl != ddl || len(right.snap.Schema) != ledgers {
				t.Fatal("precheck failure wrote an endpoint")
			}
			assertUnlocks(t, left, right)
		})
	}
}

func TestSetupFailureLeavesNoLedger(t *testing.T) {
	cause := errors.New("setup failed")
	cases := []struct {
		name   string
		stage  string
		mutate func(*trackedStore)
	}{
		{name: "database", stage: "ensure database failed", mutate: func(s *trackedStore) {
			s.databaseErr = cause
		}},
		{name: "schema ledger", stage: "ensure schema ledger failed", mutate: func(s *trackedStore) {
			s.ledgerErr = cause
		}},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
			item.mutate(store)

			err := run(Options{Type: MigrateTypeSchema}, []Store{store})
			if !errors.Is(err, cause) {
				t.Fatalf("setup error lost its cause, errmsg: %s", err)
			}
			assertErrorFields(t, err, item.stage, "endpoint: 127.0.0.1:3306")
			if store.ddl != 0 || len(store.snap.Schema) != 0 {
				t.Fatal("setup failure wrote ddl or a schema ledger row")
			}
			assertUnlocks(t, store)
		})
	}
}

func TestDataLedgerNameConflictBlocksInsert(t *testing.T) {
	cases := []struct {
		name   string
		repair bool
		keep   int
	}{
		{name: "empty table", repair: false, keep: 0},
		{name: "empty table with repair", repair: true, keep: 0},
		{name: "partial rows with repair", repair: true, keep: 1},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			store := migrated("127.0.0.1:3306", "u1")
			store.snap.Data[dataVersion] = Ledger{Version: dataVersion, Name: "other_ledger"}
			store.strategies = store.strategies[:item.keep]

			err := run(Options{Type: MigrateTypeData, RepairMissingData: item.repair}, []Store{store})
			assertErrorFields(t, err, "data ledger name conflict")
			if len(store.strategies) != item.keep {
				t.Fatalf("conflicting data ledger inserted strategies, count: %d", len(store.strategies))
			}
			if store.snap.Data[dataVersion].Name != "other_ledger" {
				t.Fatal("conflicting data ledger was rewritten")
			}
		})
	}
}

func TestInventoryProbeFailureKeepsCompletedEndpoints(t *testing.T) {
	cause := errors.New("probe failed")
	first := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	second := newTrackedStore("127.0.0.1:3307", testIdentity("u2"), &[]string{})
	second.probeErr = cause
	var output bytes.Buffer

	err := run(Options{Inventory: true, Report: &output}, []Store{first, second})
	if !errors.Is(err, cause) {
		t.Fatalf("inventory probe error lost its cause, errmsg: %s", err)
	}
	assertErrorFields(t, err, "inventory failed", "endpoint: 127.0.0.1:3307")
	report := output.String()
	if !strings.Contains(report, "endpoints: 1") || strings.Contains(report, "endpoint  127.0.0.1:3307") {
		t.Fatalf("failed endpoint was included, report: %s", report)
	}
	if !strings.Contains(report, "result: failed, endpoint: 127.0.0.1:3307, errmsg: probe failed") {
		t.Fatalf("failed result, report: %s", report)
	}
	if first.ddl != 0 || second.ddl != 0 {
		t.Fatal("inventory wrote ddl")
	}
	assertUnlocks(t, first, second)
}

func TestInventoryReportWriteFailure(t *testing.T) {
	cause := errors.New("write failed")
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})

	err := run(Options{Inventory: true, Report: errWriter{err: cause}}, []Store{store})
	if !errors.Is(err, cause) {
		t.Fatalf("report write error was dropped, errmsg: %v", err)
	}
	if store.ddl != 0 {
		t.Fatal("inventory wrote ddl")
	}
}

func TestInventoryDataLedgerConflict(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.snap.LedgerDataOK = false
	var output bytes.Buffer

	err := run(Options{Inventory: true, Report: &output}, []Store{store})
	assertErrorFields(t, err, "structural conflict")
	report := output.String()
	if !strings.Contains(report, "class: conflict") || !strings.Contains(report, "conflict  ledger: data") {
		t.Fatalf("data ledger conflict, report: %s", report)
	}
	if strings.Contains(report, "conflict  ledger: schema") || !strings.Contains(report, "result: conflict") {
		t.Fatalf("data ledger conflict result, report: %s", report)
	}
}

func TestInventoryCountsEveryClass(t *testing.T) {
	empty := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	partial := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db", Port: 3307})
	partial.snap.Tables[statusTable] = tableFromSpec(statusSpec())
	complete := migrated("127.0.0.1:3308", "u3")
	var output bytes.Buffer

	if err := run(Options{Inventory: true, Report: &output}, []Store{empty, partial, complete}); err != nil {
		t.Fatal(err)
	}
	report := output.String()
	if !strings.Contains(report, "endpoints: 3, empty: 1, partial: 1, complete: 1, conflict: 0") {
		t.Fatalf("overview counts, report: %s", report)
	}
	for endpoint, class := range map[string]string{
		"127.0.0.1:3306": classEmpty, "127.0.0.1:3307": classPartial, "127.0.0.1:3308": classComplete,
	} {
		if line := lineAfter(report, "endpoint  "+endpoint); !strings.HasPrefix(line, "class: "+class+" ") {
			t.Fatalf("endpoint class, endpoint: %s, line: %s", endpoint, line)
		}
	}
}

// migratedTracked returns a tracked store at the full schema, with its call and unlock history reset.
func migratedTracked(t *testing.T, name, uuid string) *trackedStore {
	t.Helper()
	store := newTrackedStore(name, testIdentity(uuid), &[]string{})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	*store.calls = (*store.calls)[:0]
	store.unlocks = 0
	return store
}

func hasIndex(table *Table, name string) bool {
	if table == nil {
		return false
	}
	for _, index := range table.Indexes {
		if index.Name == name {
			return true
		}
	}
	return false
}

type errWriter struct {
	err error
}

func (w errWriter) Write([]byte) (int, error) { return 0, w.err }
