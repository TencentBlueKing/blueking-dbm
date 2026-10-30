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
	"database/sql"
	"fmt"
	"strings"
	"testing"
)

func TestFactPredicatesFollowColumnType(t *testing.T) {
	integer := columnSpec{Target: columnForm{DataType: "int", Nullable: false, Unsigned: true}}
	if strings.Join(factPredicates(integer), ",") != "IS NULL,< 0" {
		t.Fatalf("integer predicates: %v", factPredicates(integer))
	}
	text := columnSpec{
		EmptyAsDefault: true,
		Target:         columnForm{DataType: "varchar", CharLen: 128, Nullable: true},
	}
	if strings.Join(factPredicates(text), ",") != "= ''" {
		t.Fatalf("string predicates: %v", factPredicates(text))
	}
}

func TestWiderIntegerAndTimestampDefaultSatisfy(t *testing.T) {
	integer := columnSpec{Target: columnForm{DataType: "int", Nullable: true}}
	if columnRelation(integer, Column{DataType: "bigint", Nullable: true}) != relSatisfy {
		t.Fatal("wider integer should satisfy the model")
	}
	stamp := columnSpec{Target: columnForm{DataType: "datetime", Nullable: true}}
	live := Column{DataType: "datetime", Nullable: true, HasDefault: true, DefaultLiteral: "CURRENT_TIMESTAMP"}
	if columnRelation(stamp, live) != relSatisfy {
		t.Fatal("timestamp default should satisfy a model without a default")
	}
}

func TestModifyClauseKeepsLiveAttributes(t *testing.T) {
	clause := columnClause("description", columnForm{
		DataType: "mediumtext", Nullable: true, Charset: "utf8mb4",
		Collation: "utf8mb4_unicode_ci", Comment: "kept", OnUpdate: "CURRENT_TIMESTAMP(3)",
		HasDefault: true, DefaultLiteral: "CURRENT_TIMESTAMP(3)",
	})
	charset := strings.Index(clause, "CHARACTER SET utf8mb4")
	nullPos := strings.Index(clause, " NULL")
	defPos := strings.Index(clause, " DEFAULT CURRENT_TIMESTAMP(3)")
	updatePos := strings.Index(clause, " ON UPDATE CURRENT_TIMESTAMP(3)")
	commentPos := strings.Index(clause, " COMMENT 'kept'")
	if charset < 0 || nullPos < charset || defPos < nullPos || updatePos < defPos || commentPos < updatePos {
		t.Fatalf("column clause order, clause: %s", clause)
	}
}

func TestStringConvergeModifyOrder(t *testing.T) {
	status := statusSpec()
	table := tableFromSpec(status)
	harvest := table.Columns["harvest_type"]
	harvest.Nullable = true
	harvest.HasDefault = false
	harvest.DefaultLiteral = ""
	harvest.Charset = "utf8mb4"
	harvest.Collation = "utf8mb4_unicode_ci"
	table.Columns["harvest_type"] = harvest
	plan := buildColumnPlan(table, status, columnByName(status, "harvest_type"))
	sql := strings.Join(plan.Statements, " ")
	want := "varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'default'"
	if !strings.Contains(sql, want) {
		t.Fatalf("harvest modify, sql: %s", sql)
	}
	snapshot, ok := tableByName("t_db_switching_snapshot_log")
	if !ok {
		t.Fatal("snapshot table is not managed")
	}
	live := tableFromSpec(snapshot)
	result := live.Columns["result"]
	result.DataType = "varchar"
	result.CharLen = 128
	result.Charset = "utf8mb4"
	live.Columns["result"] = result
	plan = buildColumnPlan(live, snapshot, columnByName(snapshot, "result"))
	sql = strings.Join(plan.Statements, " ")
	if !strings.Contains(sql, "mediumtext CHARACTER SET utf8mb4 NULL") {
		t.Fatalf("result modify, sql: %s", sql)
	}
	if strings.Index(sql, "CHARACTER SET") > strings.Index(sql, " NULL") {
		t.Fatalf("charset follows null, sql: %s", sql)
	}
}

func TestTimestampAttributesSatisfyWithoutModify(t *testing.T) {
	want := columnSpec{Target: columnForm{DataType: "datetime", Nullable: true}}
	live := Column{
		DataType: "timestamp", Nullable: false, HasDefault: true,
		DefaultLiteral: "CURRENT_TIMESTAMP(3)", OnUpdate: "CURRENT_TIMESTAMP(3)",
	}
	if columnRelation(want, live) != relSatisfy {
		t.Fatal("timestamp default should satisfy a nullable datetime model")
	}
	parsed := liveColumn(
		"created_at", "timestamp", "NO", "timestamp(3)",
		"DEFAULT_GENERATED on update CURRENT_TIMESTAMP(3)", sql.NullInt64{},
		sql.NullString{String: "current_timestamp(3)", Valid: true},
		sql.NullString{}, sql.NullString{}, sql.NullString{},
	)
	if parsed.OnUpdate != "CURRENT_TIMESTAMP(3)" || parsed.DefaultLiteral != "current_timestamp(3)" {
		t.Fatalf("live timestamp attributes, default: %s, on_update: %s", parsed.DefaultLiteral, parsed.OnUpdate)
	}
	strict := columnSpec{Target: columnForm{DataType: "datetime", Nullable: false}}
	form := modifyForm(strict, Column{
		DataType: "timestamp", Nullable: true, HasDefault: true,
		DefaultLiteral: "CURRENT_TIMESTAMP", OnUpdate: "CURRENT_TIMESTAMP",
	})
	clause := columnClause("created_at", form)
	if form.DataType != "timestamp" || !strings.Contains(clause, "timestamp NOT NULL") ||
		!strings.Contains(clause, "ON UPDATE CURRENT_TIMESTAMP") {
		t.Fatalf("modify dropped timestamp attributes, clause: %s", clause)
	}
}

func TestDuplicateSQLIgnoresNullsInNullableColumns(t *testing.T) {
	query, err := duplicateSQL("t_db_switching_strategy", []string{"name", "bk_biz_id"}, []bool{true, false})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(query, "WHERE `name` IS NOT NULL") || strings.Contains(query, "`bk_biz_id` IS NOT NULL") {
		t.Fatalf("nullable duplicate filter, query: %s", query)
	}
	if !strings.Contains(query, "GROUP BY `name`, `bk_biz_id` HAVING COUNT(*) > 1 LIMIT 1") {
		t.Fatalf("duplicate query, query: %s", query)
	}
}

func TestOnlyAlterStatementsTakeLockWait(t *testing.T) {
	if !isAlter("ALTER TABLE `t` ADD COLUMN `a` int NULL") || isAlter("UPDATE `t` SET `a` = 1") {
		t.Fatal("lock wait predicate mismatched")
	}
	if isAlter("CREATE TABLE `t` (`a` int NULL)") {
		t.Fatal("create table is not an alter")
	}
	if !isUpdate("UPDATE `t` SET `a` = 1") || isUpdate("SET @dbha_migrate_n := 0") || isUpdate("ALTER TABLE `t`") {
		t.Fatal("backfill predicate mismatched")
	}
}

func TestBackfillStatementsAreBatched(t *testing.T) {
	limit := fmt.Sprintf(" LIMIT %d", convergeBatchRows)
	statements := append([]string{
		nullFillSQL("t", "a", "'x'"),
		emptyFillSQL("t", "a", "'x'"),
	}, assignStatements("t", "id", []string{"k"})...)
	for _, statement := range statements {
		if isUpdate(statement) && !strings.HasSuffix(statement, limit) {
			t.Fatalf("backfill is not batched, statement: %s", statement)
		}
	}
	if !strings.Contains(statements[3], "ORDER BY `k` LIMIT") {
		t.Fatalf("id assignment lost its order, statement: %s", statements[3])
	}
}

func TestEmptyLedgerSkipsReseed(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.strategies = nil
	if len(store.snap.Data) != 1 {
		t.Fatal("migrated store has no data ledger")
	}
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != 0 || len(store.snap.Data) != 1 {
		t.Fatal("empty recorded strategy table was reseeded or the ledger was rewritten")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if len(store.strategies) != len(defaultStrategies()) {
		t.Fatal("repair did not reseed the empty strategy table")
	}
}

func TestDuplicateUniqueIndexBlocksPrecheck(t *testing.T) {
	left := migrated("127.0.0.1:3306", "u1")
	right := migrated("127.0.0.1:3307", "u2")
	step := findStep(objectIndex, strategyTableName(), "", "idx_biz_event_reason")
	delete(left.snap.Schema, step.Version)
	table := left.snap.Tables[strategyTableName()]
	kept := table.Indexes[:0]
	for _, index := range table.Indexes {
		if index.Name != "idx_biz_event_reason" {
			kept = append(kept, index)
		}
	}
	table.Indexes = kept
	left.duplicates = map[string]bool{
		duplicateKey(strategyTableName(), []string{
			"bk_biz_id", "trigger_event_name", "trigger_event_name_reason",
		}): true,
	}
	leftDDL, rightDDL := left.ddl, right.ddl
	err := run(Options{Type: MigrateTypeSchema}, []Store{left, right})
	if err == nil || !strings.Contains(err.Error(), "result: duplicate") {
		t.Fatalf("duplicate index was not blocked, errmsg: %v", err)
	}
	if left.ddl != leftDDL || right.ddl != rightDDL {
		t.Fatal("duplicate precheck wrote ddl")
	}
}

func TestNullColumnBlocksNotNullConverge(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	column := store.snap.Tables[statusTable].Columns["machine_id"]
	column.Nullable = true
	column.HasNull = true
	store.snap.Tables[statusTable].Columns["machine_id"] = column
	ddl := store.ddl
	err := run(Options{Type: MigrateTypeSchema}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "result: not_null") {
		t.Fatalf("null column was not blocked, errmsg: %v", err)
	}
	if store.ddl != ddl {
		t.Fatal("null column precheck wrote ddl")
	}
}

func TestNotNullColumnBlocksNonEmptyTable(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	delete(store.snap.Tables[statusTable].Columns, "machine_id")
	delete(store.snap.Schema, findStep(objectColumn, statusTable, "machine_id", "").Version)
	delete(store.snap.Schema, findStep(objectColumnDef, statusTable, "machine_id", "").Version)
	store.nonEmpty = map[string]bool{statusTable: true}
	ddl := store.ddl
	err := run(Options{Type: MigrateTypeSchema}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "result: not_null") {
		t.Fatalf("missing not null column was not blocked, errmsg: %v", err)
	}
	if store.ddl != ddl {
		t.Fatal("not null precheck wrote ddl")
	}
}

func TestRejectedOptionCombinations(t *testing.T) {
	rejected := []Options{
		{Inventory: true, RepairMissing: true},
		{Inventory: true, RepairMissingSchema: true},
		{InventoryFull: true, RepairMissingData: true},
		{Type: MigrateTypeSchema, RepairMissingData: true},
		{Type: MigrateTypeData, RepairMissingSchema: true},
	}
	for _, opts := range rejected {
		if err := validateOptions(opts); err == nil {
			t.Fatalf("combination was accepted, type: %s, inventory: %t", opts.Type, opts.Inventory)
		}
	}
}

func TestServerIDFallbackDoesNotAliasDistinctHosts(t *testing.T) {
	left := newMem("127.0.0.1:3306", Identity{
		ServerUUID: "server-id:1", Hostname: "db-a", Port: 3306, Fallback: true,
	})
	right := newMem("127.0.0.1:3307", Identity{
		ServerUUID: "server-id:1", Hostname: "db-b", Port: 3307, Fallback: true,
	})
	targets, err := orderStores([]Store{left, right})
	if err != nil || len(targets.migrate) != 2 || len(targets.aliases) != 0 {
		t.Fatalf("fallback hosts were aliased, migrate: %d, errmsg: %v", len(targets.migrate), err)
	}
	same := newMem("127.0.0.1:3306", Identity{
		ServerUUID: "server-id:1", Hostname: "db-a", Port: 3306, Fallback: true,
	})
	targets, err = orderStores([]Store{left, same})
	if err != nil || len(targets.migrate) != 1 || len(targets.aliases) != 1 {
		t.Fatalf("same fallback endpoint was not reused, migrate: %d, errmsg: %v", len(targets.migrate), err)
	}
}

func TestOrdinaryStepsSkipFactProbe(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	for _, step := range schemaSteps() {
		if convergeKind(step.Kind) {
			continue
		}
		store.probes = nil
		if err := applyStep(store, Options{Type: MigrateTypeSchema}, step, false, &migrateResult{}); err != nil {
			t.Fatal(err)
		}
		if len(store.probes) != 0 {
			t.Fatalf("ordinary step probed facts, name: %s", step.Name)
		}
	}
}

func TestLivePredicatesSkipImpossibleMatches(t *testing.T) {
	spec := columnSpec{Name: "c", EmptyAsDefault: true, Target: columnForm{DataType: "bigint", Unsigned: true}}
	cases := []struct {
		name string
		live Column
		want []string
	}{
		{name: "nullable signed", live: Column{Nullable: true}, want: []string{"IS NULL", "< 0", "= ''"}},
		{name: "not null", live: Column{}, want: []string{"< 0", "= ''"}},
		{name: "unsigned", live: Column{Nullable: true, Unsigned: true}, want: []string{"IS NULL", "= ''"}},
		{name: "not null unsigned", live: Column{Unsigned: true}, want: []string{"= ''"}},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			got := livePredicates(spec, item.live)
			if strings.Join(got, "|") != strings.Join(item.want, "|") {
				t.Fatalf("live predicates, got: %v, want: %v", got, item.want)
			}
		})
	}
}

func TestServerIDFallbackKeepsDistinctServersOnSameHostPort(t *testing.T) {
	left := newMem("127.0.0.1:3306", Identity{
		ServerUUID: "server-id:1", Hostname: "mysql-0", Port: 3306, Fallback: true,
	})
	right := newMem("127.0.0.1:3307", Identity{
		ServerUUID: "server-id:2", Hostname: "mysql-0", Port: 3306, Fallback: true,
	})
	targets, err := orderStores([]Store{left, right})
	if err != nil || len(targets.migrate) != 2 || len(targets.aliases) != 0 {
		t.Fatalf("distinct fallback servers were aliased, migrate: %d, errmsg: %v", len(targets.migrate), err)
	}
}

func TestProbeScopeStaysOnStep(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.probes = nil
	step := findStep(objectColumnDef, statusTable, "machine_id", "")
	if err := applyStep(store, Options{Type: MigrateTypeSchema}, step, false, &migrateResult{}); err != nil {
		t.Fatal(err)
	}
	if len(store.probes) == 0 {
		t.Fatal("step did not probe")
	}
	for _, probe := range store.probes {
		if probe.Table != statusTable || probe.Column != "machine_id" {
			t.Fatalf("probe left the step, table: %s, column: %s", probe.Table, probe.Column)
		}
	}
}
