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
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

func TestSchemaStepsAreMonotonic(t *testing.T) {
	names := map[string]bool{}
	versions := map[int64]bool{}
	var maxPublished int64
	for _, step := range publishedSchemaSteps() {
		if step.Version <= maxPublished {
			t.Fatalf("published version is not monotonic, version: %d", step.Version)
		}
		maxPublished = step.Version
	}
	seenConverge := false
	for _, step := range schemaSteps() {
		if versions[step.Version] {
			t.Fatalf("duplicate step version, version: %d", step.Version)
		}
		versions[step.Version] = true
		if names[step.Name] {
			t.Fatalf("duplicate step name, name: %s", step.Name)
		}
		names[step.Name] = true
		if convergeKind(step.Kind) {
			seenConverge = true
			continue
		}
		if seenConverge {
			t.Fatalf("ordinary step follows converge, version: %d", step.Version)
		}
	}
	if (Options{Type: "strategy"}).ValidType() {
		t.Fatal("strategy is not a migrate type")
	}
}

func TestIndexEquivalence(t *testing.T) {
	have := []Index{{
		Name: "other", Unique: false, Columns: []string{"description"}, Prefix: []int{0},
	}}
	want := indexSpec{Name: "idx_description", Unique: false, Columns: []string{"description"}, Prefix: []int{255}}
	present, conflict := matchIndex(have, want)
	if !present || conflict {
		t.Fatal("full column index should satisfy a prefix index")
	}
	short := []Index{{
		Name: "other", Unique: false, Columns: []string{"description"}, Prefix: []int{10},
	}}
	present, conflict = matchIndex(short, want)
	if present || conflict {
		t.Fatal("shorter prefix is not equivalent")
	}
	unique := []Index{{
		Name: "other", Unique: false, Columns: []string{"name", "bk_biz_id"},
	}}
	wantUnique := indexSpec{Name: "idx_name", Unique: true, Columns: []string{"name", "bk_biz_id"}}
	present, conflict = matchIndex(unique, wantUnique)
	if present || !conflict {
		t.Fatal("unique mismatch is a conflict")
	}
}

func TestEmptyDatabaseIsIdempotent(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	opts := Options{Type: MigrateTypeAll}
	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.snap.Tables[statusTable] == nil || !sameCols(store.snap.Tables[statusTable].PK, statusSpec().Baseline) {
		t.Fatal("new status table should use the harvest_type primary key")
	}
	if len(store.strategies) != len(defaultStrategies()) {
		t.Fatalf("strategy count: %d", len(store.strategies))
	}
	ddl := store.ddl
	updated := strategyStamp(store)
	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != ddl {
		t.Fatalf("second run executed ddl, before: %d, after: %d", ddl, store.ddl)
	}
	if strategyStamp(store) != updated {
		t.Fatal("second run changed strategy rows")
	}
}

func TestPartialTablesRequireRepair(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	store.snap.Tables[statusTable] = tableFromSpec(statusSpec())
	store.snap.Tables["t_db_switching_strategy"] = withIndexes(strategySpec())
	seed := defaultStrategies()[0]
	store.strategies = []StrategyState{{
		BkBizID: 0, Event: seed.TriggerEventName.String(), Reason: int(seed.TriggerEventNameReason), Priority: 1,
		UpdatedAt: "kept",
	}}
	err := run(Options{Type: MigrateTypeAll}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "result: need_repair") {
		t.Fatalf("partial tables should fail closed with need_repair, errmsg: %v", err)
	}
	if store.ddl != 0 || store.strategies[0].UpdatedAt != "kept" {
		t.Fatal("failed precheck wrote data")
	}
	if err := run(Options{Type: MigrateTypeAll, RepairMissingSchema: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.snap.Tables[statusTable] == nil || store.strategies[0].Priority != 1 {
		t.Fatal("existing table or edited strategy changed")
	}
	if len(store.strategies) != 1 || len(store.snap.Data) != 0 {
		t.Fatal("existing strategy data inserted missing rows or a data ledger")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.strategies[0].Priority != 1 || len(store.strategies) != len(defaultStrategies()) {
		t.Fatal("repair-missing-data did not insert only the missing rows")
	}
}

func TestDriftAndRepair(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Tables[statusTable].Columns, "probe")
	ddl := store.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("recorded column loss should be drift")
	}
	if store.ddl != ddl {
		t.Fatal("drift wrote ddl")
	}
	opts := Options{Type: MigrateTypeSchema, RepairMissing: true}
	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if _, ok := store.snap.Tables[statusTable].Columns["probe"]; !ok {
		t.Fatal("repair did not restore the column")
	}
	repaired := store.ddl
	if err := run(opts, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != repaired {
		t.Fatal("second repair executed ddl")
	}
}

func TestRepairMissingTable(t *testing.T) {
	for _, opts := range []Options{
		{Type: MigrateTypeSchema, RepairMissingSchema: true},
		{Type: MigrateTypeSchema, RepairMissing: true},
	} {
		store := migrated("127.0.0.1:3306", "u1")
		delete(store.snap.Tables, "t_db_switching_log")
		ddl := store.ddl
		err := run(Options{Type: MigrateTypeSchema}, []Store{store})
		if err == nil || !strings.Contains(err.Error(), "result: drift") {
			t.Fatalf("recorded table loss should be drift, errmsg: %v", err)
		}
		if store.ddl != ddl {
			t.Fatal("drift wrote ddl")
		}
		if err = run(opts, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if store.snap.Tables["t_db_switching_log"] == nil {
			t.Fatalf("table was not rebuilt, repair_missing: %t", opts.RepairMissing)
		}
	}
}

func TestConflictDoesNotWrite(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	table := tableFromSpec(statusSpec())
	table.PK = []string{"id"}
	store.snap.Tables[statusTable] = table
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("unknown primary key should conflict")
	}
	if store.ddl != 0 || len(store.snap.Schema) != 0 {
		t.Fatal("conflict wrote schema")
	}
}

func TestLedgerFailureRetriesWithoutDDL(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Schema, 1)
	applied := append([]string{}, store.applied...)
	store.failRecord = true
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("ledger failure should surface")
	}
	if len(store.applied) != len(applied) {
		t.Fatal("ledger failure executed ddl")
	}
	if _, ok := store.snap.Schema[1]; ok {
		t.Fatal("failed ledger write left a version row")
	}
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if _, ok := store.snap.Schema[1]; !ok {
		t.Fatal("retry did not record the ledger")
	}
	if len(store.applied) != len(applied) {
		t.Fatal("retry repeated ddl")
	}
}

func TestDataTransactionRollsBack(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	store.txFail = true
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
		t.Fatal("transaction failure should surface")
	}
	if len(store.strategies) != 0 || len(store.snap.Data) != 0 {
		t.Fatal("failed data step left rows or a ledger")
	}
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != len(defaultStrategies()) {
		t.Fatal("retry did not insert strategies")
	}
}

func TestDataRequiresStrategyTable(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
		t.Fatal("data mode should not create business tables")
	}
	if store.ddl != 0 {
		t.Fatal("data mode executed ddl")
	}
}

func TestPrecheckStopsEveryEndpoint(t *testing.T) {
	left := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db-a", Port: 3306})
	right := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db-b", Port: 3307})
	right.snap.ReadOnly = true
	if err := run(Options{Type: MigrateTypeAll}, []Store{left, right}); err == nil {
		t.Fatal("read only endpoint should stop the batch")
	}
	if left.ddl != 0 || right.ddl != 0 {
		t.Fatal("precheck failure wrote an endpoint")
	}
}

func TestLaterEndpointFailureConverges(t *testing.T) {
	left := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db-a", Port: 3306})
	right := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db-b", Port: 3307})
	right.failDDL = true
	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err == nil {
		t.Fatal("second endpoint should fail")
	}
	leftDDL := left.ddl
	if leftDDL == 0 || len(right.snap.Schema) != 0 {
		t.Fatal("first endpoint should stay applied and the second should stay unrecorded")
	}
	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err != nil {
		t.Fatal(err)
	}
	if left.ddl != leftDDL || right.ddl == 0 {
		t.Fatal("rerun should keep the first endpoint idle and finish the second")
	}
	again := left.ddl
	rightDDL := right.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err != nil {
		t.Fatal(err)
	}
	if left.ddl != again || right.ddl != rightDDL {
		t.Fatal("converged endpoints changed on the third run")
	}
}

func TestIdentityConflictAndAlias(t *testing.T) {
	cloneA := newMem("127.0.0.1:3306", Identity{ServerUUID: "same", Hostname: "db-a", Port: 3306})
	cloneB := newMem("127.0.0.1:3307", Identity{ServerUUID: "same", Hostname: "db-b", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{cloneA, cloneB}); err == nil {
		t.Fatal("cloned server_uuid should conflict")
	}
	if cloneA.ddl != 0 || cloneB.ddl != 0 {
		t.Fatal("identity conflict wrote an endpoint")
	}
	aliasA := newMem("127.0.0.1:3306", Identity{ServerUUID: "one", Hostname: "db", Port: 3306})
	aliasB := newMem("127.0.0.1:3306", Identity{ServerUUID: "one", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{aliasA, aliasB}); err != nil {
		t.Fatal(err)
	}
	if aliasA.ddl == 0 && aliasB.ddl == 0 || aliasA.ddl > 0 && aliasB.ddl > 0 {
		t.Fatal("same instance aliases should migrate once")
	}
}

func TestLockSerializesCallers(t *testing.T) {
	first := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	second := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := first.Lock(); err != nil {
		t.Fatal(err)
	}
	done := make(chan struct{})
	go func() {
		_ = second.Lock()
		close(done)
		_ = second.Unlock()
	}()
	select {
	case <-done:
		t.Fatal("second lock did not wait")
	case <-time.After(30 * time.Millisecond):
	}
	if err := first.Unlock(); err != nil {
		t.Fatal(err)
	}
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("second lock stayed blocked")
	}
}

func TestStatusPrimaryKeyConvergesWithSchema(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.snap.Tables[statusTable].PK = legacyStatusKey()
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.pkAlters != 1 || !sameCols(store.snap.Tables[statusTable].PK, statusSpec().Baseline) {
		t.Fatal("schema did not converge the legacy primary key once")
	}
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.pkAlters != 1 {
		t.Fatal("second schema run changed the primary key again")
	}
}

func TestInventoryIsReadOnly(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Inventory: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != 0 || store.snap.Database {
		t.Fatal("inventory wrote the database")
	}
	class, _, _ := classify(store.snap)
	if class != classEmpty {
		t.Fatalf("class: %s", class)
	}
}

func TestRunRejectsStrategyType(t *testing.T) {
	if err := Run(Options{Type: "strategy"}); err == nil {
		t.Fatal("strategy type should fail")
	}
}

func TestSchemaDoesNotInsertStrategies(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != 0 || len(store.snap.Data) != 0 {
		t.Fatal("schema mode inserted strategy rows or a data ledger")
	}
	if len(store.snap.Schema) == 0 || store.snap.Tables["t_db_switching_log"] == nil {
		t.Fatal("schema mode did not create the business tables and schema ledger")
	}
}

func TestIncompleteObjectsAreAdditive(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	for _, spec := range modelTables() {
		store.snap.Tables[spec.Name] = withIndexes(spec)
	}
	status := store.snap.Tables[statusTable]
	delete(status.Columns, "probe")
	delete(status.Columns, "harvest_type")
	status.Columns["extra"] = Column{Name: "extra", DataType: "varchar"}
	store.snap.Tables[strategyTableName()].Indexes = nil
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if _, ok := status.Columns["probe"]; !ok {
		t.Fatal("missing probe column was not added")
	}
	if _, ok := status.Columns["harvest_type"]; !ok {
		t.Fatal("missing harvest_type column was not added")
	}
	if status.Columns["extra"].DataType != "varchar" || !sameCols(status.PK, statusSpec().Baseline) {
		t.Fatal("additive migrate changed an existing column or the primary key")
	}
	if len(store.snap.Tables[strategyTableName()].Indexes) == 0 {
		t.Fatal("missing secondary indexes were not added")
	}
	ddl := store.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != ddl {
		t.Fatal("second run changed the structure")
	}
}

func TestExistingStrategiesOnlyRecordLedger(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Data, dataVersion)
	for i := range store.strategies {
		store.strategies[i].Priority = 1
		store.strategies[i].UpdatedAt = "edited"
	}
	ddl := store.ddl
	stamp := strategyStamp(store)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != ddl || strategyStamp(store) != stamp {
		t.Fatal("existing strategies were rewritten")
	}
	if _, ok := store.snap.Data[dataVersion]; !ok {
		t.Fatal("missing data ledger was not recorded")
	}
}

func TestSecondProcessBecomesNoop(t *testing.T) {
	first := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	second := &memStore{memServer: first.memServer, endpoint: "127.0.0.1:3306", ident: first.ident, snap: first.snap}
	release := make(chan struct{})
	locked := make(chan struct{})
	go func() {
		if err := first.Lock(); err != nil {
			t.Errorf("lock failed, errmsg: %s", err)
			return
		}
		close(locked)
		<-release
		if err := applyOne(first, Options{Type: MigrateTypeAll}); err != nil {
			t.Errorf("apply failed, errmsg: %s", err)
		}
		_ = first.Unlock()
	}()
	<-locked
	done := make(chan error, 1)
	go func() {
		done <- run(Options{Type: MigrateTypeAll}, []Store{second})
	}()
	select {
	case err := <-done:
		t.Fatalf("second process did not wait, errmsg: %v", err)
	case <-time.After(30 * time.Millisecond):
	}
	close(release)
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	if second.ddl != 0 || len(second.strategies) != len(defaultStrategies()) {
		t.Fatal("second process repeated ddl or strategy rows")
	}
}

func TestInventoryProfileAndLegacyKeys(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	store.snap.Version = "8.0.36-MariaDB"
	status := tableFromSpec(statusSpec())
	status.PK = legacyStatusKey()
	store.snap.Tables[statusTable] = status
	store.snap.RowCounts[statusTable] = 4
	strategy := tableFromSpec(strategySpec())
	strategy.PK = []string{"bk_biz_id", "trigger_event_name", "trigger_event_name_reason"}
	store.snap.Tables[strategyTableName()] = strategy
	notes := legacyKeyNotes(store.snap)
	if len(notes) != 2 {
		t.Fatalf("legacy notes: %v", notes)
	}
	profiles := inventoryProfiles(store.snap)
	if profiles[0].Rows != 4 || profiles[0].PK == "-" || versionText(store.snap) != store.snap.Version {
		t.Fatalf("profile rows: %d, pk: %s", profiles[0].Rows, profiles[0].PK)
	}
	if err := run(Options{Inventory: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != 0 {
		t.Fatal("inventory wrote ddl")
	}
}

func legacyStatusKey() []string {
	return hamodel.DbhaDataStatus{}.MigrateKnownPKs()[0]
}

func strategyTableName() string {
	return "t_db_switching_strategy"
}

func migrated(endpoint, uuid string) *memStore {
	store := newMem(endpoint, Identity{ServerUUID: uuid, Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		panic(err)
	}
	return store
}

func withIndexes(spec tableSpec) *Table {
	table := tableFromSpec(spec)
	for _, index := range spec.Indexes {
		table.Indexes = append(table.Indexes, Index{
			Name: index.Name, Unique: index.Unique, Columns: append([]string{}, index.Columns...),
			Prefix: append([]int{}, index.Prefix...),
		})
	}
	return table
}

func strategyStamp(store *memStore) string {
	var stamp string
	for _, row := range store.strategies {
		stamp += row.Event + row.UpdatedAt
	}
	return stamp
}
