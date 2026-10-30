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
	"strconv"
	"strings"
	"testing"
)

func TestRecordedRunLogsOnlyEndpointSummary(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.strategies = append(store.strategies, StrategyState{
		BkBizID: 9, Event: "custom_event", Priority: 1, UpdatedAt: "kept",
	})
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if infoHas(recorded, "phase: check") {
		t.Fatal("satisfied steps logged a check phase")
	}
	if infoHas(recorded, "schema changed") || infoHas(recorded, "default strategy") {
		t.Fatal("unchanged objects were logged individually")
	}
	if infoHas(recorded, "trigger_event_name: custom_event") {
		t.Fatal("custom strategy row was logged")
	}
	if !infoHas(
		recorded,
		"migrate finished, endpoint: "+store.Endpoint(),
		"schema_unchanged: "+strconv.Itoa(len(schemaSteps())),
		"schema_created: 0",
		"schema_repaired: 0",
		"schema_converged: 0",
		"data_unchanged: "+strconv.Itoa(len(defaultStrategies())),
		"data_initialized: 0",
		"data_repaired: 0",
		"data_skipped: 0",
		"data_kept_deleted: 0",
	) {
		t.Fatalf("missing endpoint summary, infos: %v", recorded.infos)
	}
	if countInfo(recorded, "migrate finished") != 1 {
		t.Fatalf("endpoint summary count, infos: %v", recorded.infos)
	}
}

func TestFirstInstallLogsCreateAndInitialize(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "schema changed", "action: create", "object: table") {
		t.Fatal("first table create was not logged")
	}
	if infoHas(recorded, "schema changed", "action: repair") {
		t.Fatal("first install logged a repair")
	}
	if !infoHas(recorded, "default strategy", "action: initialize", "bk_biz_id: 0") {
		t.Fatal("first data insert was not logged")
	}
	if !infoHas(recorded, "data_initialized: "+strconv.Itoa(len(defaultStrategies()))) {
		t.Fatal("summary did not count initialized identities")
	}
	assertLogsOmitSQLAndRowBody(t, recorded)
}

func TestSchemaOnlySummaryHasZeroDataCounts(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if infoHas(recorded, "action: initialize") || infoHas(recorded, "action: repair") {
		t.Fatal("schema-only run logged a data write")
	}
	if !infoHas(
		recorded,
		"data_unchanged: 0",
		"data_initialized: 0",
		"data_repaired: 0",
		"data_skipped: 0",
		"data_kept_deleted: 0",
	) {
		t.Fatalf("schema-only summary counted data, infos: %v", recorded.infos)
	}
}

func TestRepairedPartialTablesLogCreate(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	store.snap.Tables[statusTable] = tableFromSpec(statusSpec())
	store.snap.Tables[strategyTableName()] = withIndexes(strategySpec())
	recorded := captureWarn(t)
	err := run(Options{Type: MigrateTypeSchema, RepairMissingSchema: true}, []Store{store})
	if err != nil {
		t.Fatal(err)
	}
	if !infoHas(
		recorded, "schema changed", "action: create", "object: table", "target: t_db_switching_log",
	) {
		t.Fatalf("accepted table was not logged as create, infos: %v", recorded.infos)
	}
	if infoHas(recorded, "schema changed", "action: repair") {
		t.Fatal("accepted missing table was logged as repair")
	}
}

func TestRepairMissingLogsColumn(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Tables[statusTable].Columns, "probe")
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeSchema, RepairMissing: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "schema changed", "action: repair", "object: column", statusTable+".probe") {
		t.Fatalf("missing column repair log, infos: %v", recorded.infos)
	}
}

func TestRepairMissingTableLogsTable(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Tables, "t_db_switching_log")
	recorded := captureWarn(t)
	err := run(Options{Type: MigrateTypeSchema, RepairMissingSchema: true}, []Store{store})
	if err != nil {
		t.Fatal(err)
	}
	if !infoHas(
		recorded, "schema changed", "action: repair", "object: table", "target: t_db_switching_log",
	) {
		t.Fatalf("missing table repair log, infos: %v", recorded.infos)
	}
}

func TestRepairMissingDataLogsIdentity(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	kept := store.strategies[0]
	store.strategies = []StrategyState{kept}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "default strategy", "action: repair", "trigger_event_name: "+otherEvent(kept.Event)) {
		t.Fatalf("missing data repair log, infos: %v", recorded.infos)
	}
	for _, seed := range defaultStrategies() {
		if seed.TriggerEventName.String() == kept.Event {
			continue
		}
		reason := "trigger_event_name_reason: " + strconv.Itoa(int(seed.TriggerEventNameReason))
		if !infoHas(recorded, "trigger_event_name: "+seed.TriggerEventName.String()+", "+reason) {
			t.Fatalf("data repair log missed the reason, infos: %v", recorded.infos)
		}
	}
	if infoHas(recorded, "trigger_event_name: "+kept.Event) {
		t.Fatal("existing identity was logged")
	}
	if !infoHas(recorded, "data_unchanged: 1", "data_repaired: 4", "data_initialized: 0") {
		t.Fatalf("data repair summary, infos: %v", recorded.infos)
	}
	assertLogsOmitSQLAndRowBody(t, recorded)
}

func TestSkippedIdentitiesStayInSummary(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.strategies = store.strategies[:1]
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "action: skip") {
		t.Fatal("missing identity was not logged as skip")
	}
	if !infoHas(recorded, "data_skipped: 4", "data_unchanged: 1", "data_initialized: 0", "data_repaired: 0") {
		t.Fatalf("skip summary, infos: %v", recorded.infos)
	}
}

func TestEmptyConvergePlanDoesNotLogChange(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	saw := false
	for _, step := range schemaSteps() {
		if step.Kind != objectColumnDef && step.Kind != objectPrimaryKey {
			continue
		}
		saw = true
		snap, err := stepSnapshot(store, step)
		if err != nil {
			t.Fatal(err)
		}
		changed, err := applyConvergeStep(store, step, snap)
		if err != nil || changed {
			t.Fatalf(
				"satisfied plan was not empty, name: %s, changed: %v, errmsg: %v",
				step.Name, changed, err,
			)
		}
	}
	if !saw {
		t.Fatal("catalog has no column definition or primary key step")
	}
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if infoHas(recorded, "schema changed") {
		t.Fatal("satisfied column or primary key logged a schema change")
	}
}

func TestFailedConvergeVerifyDoesNotCount(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	var step schemaStep
	for _, candidate := range schemaSteps() {
		if candidate.Kind == objectColumnDef {
			step = candidate
			break
		}
	}
	recorded := captureWarn(t)
	result := &migrateResult{}
	err := applyStep(store, Options{Type: MigrateTypeSchema}, step, false, result)
	if err == nil {
		t.Fatal("missing column should fail verification")
	}
	if infoHas(recorded, "schema changed") || infoHas(recorded, "migrate finished") {
		t.Fatal("failed verification logged success")
	}
	if result.schemaUnchanged != 0 || result.schemaConverged != 0 {
		t.Fatalf(
			"failed verification was counted, unchanged: %d, converged: %d",
			result.schemaUnchanged, result.schemaConverged,
		)
	}
}

func TestDataTransactionFailureDoesNotLogSuccess(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	store.txFail = true
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
		t.Fatal("transaction failure should surface")
	}
	if infoHas(recorded, "action: initialize") || infoHas(recorded, "action: repair") {
		t.Fatalf("failed data step logged a successful write, infos: %v", recorded.infos)
	}
	if infoHas(recorded, "migrate finished") {
		t.Fatal("failed endpoint logged a summary")
	}
}

func TestLaterSchemaFailureKeepsEarlierChangeLog(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	recorded := captureWarn(t)
	result := &migrateResult{}
	err := applyStep(store, Options{Type: MigrateTypeSchema}, schemaSteps()[0], false, result)
	if err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "schema changed", "action: create") {
		t.Fatal("successful create was not logged")
	}
	store.failDDL = true
	if err = applySchema(store, Options{Type: MigrateTypeSchema}, result); err == nil {
		t.Fatal("later schema step should fail")
	}
	if infoHas(recorded, "migrate finished") {
		t.Fatal("failed endpoint logged a summary")
	}
	if !infoHas(recorded, "schema changed", "action: create") {
		t.Fatal("successful object log disappeared")
	}
}

func otherEvent(kept string) string {
	for _, seed := range defaultStrategies() {
		if seed.TriggerEventName.String() != kept {
			return seed.TriggerEventName.String()
		}
	}
	return ""
}

func countInfo(recorded *warnLog, part string) int {
	count := 0
	for _, line := range recorded.infos {
		if strings.Contains(line, part) {
			count++
		}
	}
	return count
}

func assertLogsOmitSQLAndRowBody(t *testing.T, recorded *warnLog) {
	t.Helper()
	banned := []string{
		"CREATE TABLE", "ALTER TABLE", "INSERT INTO", "priority: 9999", "trigger_count", "action: switch",
	}
	for _, line := range recorded.infos {
		for _, part := range banned {
			if strings.Contains(line, part) {
				t.Fatalf("log contains forbidden text, text: %s, line: %s", part, line)
			}
		}
	}
}
