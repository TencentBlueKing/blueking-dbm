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
	"reflect"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestPublishedSchemaSQLStaysStable(t *testing.T) {
	for table, create := range map[string]string{
		statusTable:         publishedStatusCreate,
		"t_dbm_metadata":    publishedMetadataCreate,
		"t_skip_dbinstance": publishedSkipCreate,
	} {
		step := findStep(objectTable, table, "", "")
		if step.Apply != create {
			t.Fatalf("create SQL changed, table: %s", table)
		}
	}
	for _, step := range schemaSteps() {
		if strings.Contains(step.Apply, "CURRENT_TIMESTAMP") {
			t.Fatalf("database time default generated, version: %d", step.Version)
		}
		if exemptPublishedChange(step) {
			continue
		}
		if step.Kind == objectColumnDef || step.Kind == objectPrimaryKey {
			t.Fatalf("converge step was not exempt, version: %d", step.Version)
		}
	}
	logCreate := findStep(objectTable, "t_db_switching_log", "", "").Apply
	if !strings.Contains(logCreate, "`id` bigint unsigned NOT NULL AUTO_INCREMENT") {
		t.Fatal("switching log id create did not become unsigned")
	}
	snapshotCreate := findStep(objectTable, "t_db_switching_snapshot_log", "", "").Apply
	if !strings.Contains(snapshotCreate, "`result` mediumtext NULL") {
		t.Fatal("snapshot result create did not become mediumtext")
	}
	strategyCreate := findStep(objectTable, strategyTableName(), "", "").Apply
	wantPK := "PRIMARY KEY (`id`, `bk_biz_id`, `trigger_event_name`, `trigger_event_name_reason`)"
	if !strings.Contains(strategyCreate, wantPK) {
		t.Fatal("strategy create primary key is not the model key")
	}
	idAdd := findStep(objectColumn, strategyTableName(), "id", "").Apply
	if !strings.Contains(idAdd, "NOT NULL AUTO_INCREMENT") || !strings.Contains(idAdd, "idx_migrate_id") {
		t.Fatal("strategy id add did not keep auto increment and the helper index")
	}
	machine := findStep(objectColumn, statusTable, "machine_id", "").Apply
	if machine != "ALTER TABLE `t_dbha_status` ADD COLUMN `machine_id` varchar(128) NULL" {
		t.Fatal("status column SQL changed")
	}
	harvest := findStep(objectColumn, statusTable, "harvest_type", "").Apply
	wantHarvest := "ALTER TABLE `t_dbha_status` ADD COLUMN `harvest_type` varchar(32) NOT NULL DEFAULT 'default'"
	if harvest != wantHarvest {
		t.Fatal("harvest_type column SQL changed")
	}
	deleted := findStep(objectIndex, "t_dbm_metadata", "", "idx_deleted_at").Apply
	if deleted != "ALTER TABLE `t_dbm_metadata` ADD INDEX `idx_deleted_at` (`deleted_at`)" {
		t.Fatal("metadata index SQL changed")
	}
	name := findStep(objectColumn, strategyTableName(), "name", "").Apply
	if name != "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `name` varchar(128) NULL" {
		t.Fatal("strategy name column SQL changed")
	}
	result := columnByName(mustSpec(t, "t_db_switching_snapshot_log"), "result")
	if result.Historical != "varchar(128)" || result.Target.DataType != "mediumtext" {
		t.Fatal("result historical type was not kept separate from the model type")
	}
}

func TestModelColumnOrderAndIndexes(t *testing.T) {
	status := mustSpec(t, statusTable)
	if status.Columns[4].Name != "harvest_type" || status.Columns[4].Target.DefaultLiteral != "default" {
		t.Fatal("harvest_type default or position changed")
	}
	metadata := mustSpec(t, "t_dbm_metadata")
	if !catalogHasColumn(metadata, "logcial_city_name") {
		t.Fatal("historical city column spelling changed")
	}
	skip := mustSpec(t, "t_skip_dbinstance")
	for _, name := range skip.Baseline {
		if name == "instance_port" {
			t.Fatal("instance_port entered the skip primary key")
		}
	}
	strategy := mustSpec(t, strategyTableName())
	var unique indexSpec
	for _, index := range strategy.Indexes {
		if index.Name == "idx_name" {
			unique = index
		}
		if index.Name == "idx_description" && (len(index.Prefix) == 0 || index.Prefix[0] != 255) {
			t.Fatal("description prefix index changed")
		}
	}
	if !unique.Unique || !sameCols(unique.Columns, []string{"name", "bk_biz_id"}) {
		t.Fatal("strategy unique index changed")
	}
}

func TestColumnDefinitionRelations(t *testing.T) {
	varchar128 := columnSpec{Target: columnForm{DataType: "varchar", CharLen: 128, Nullable: true}}
	if columnRelation(varchar128, Column{DataType: "varchar", CharLen: 255, Nullable: true}) != relSatisfy {
		t.Fatal("wider varchar should satisfy the model")
	}
	if columnRelation(varchar128, Column{DataType: "text", Nullable: true}) != relConflict {
		t.Fatal("text should not satisfy varchar")
	}
	textCol := columnSpec{Target: columnForm{DataType: "text", Nullable: true}}
	if columnRelation(textCol, Column{DataType: "mediumtext", Nullable: true}) != relSatisfy {
		t.Fatal("mediumtext should satisfy text")
	}
	if columnRelation(textCol, Column{DataType: "longtext", Nullable: true}) != relSatisfy {
		t.Fatal("longtext should satisfy text")
	}
	medium := columnSpec{
		Historical: "varchar(128)",
		Target:     columnForm{DataType: "mediumtext", Nullable: true},
	}
	if columnRelation(medium, Column{DataType: "varchar", CharLen: 128, Nullable: true}) != relSafe {
		t.Fatal("historical varchar should widen to mediumtext")
	}
	if columnRelation(medium, Column{DataType: "longtext", Nullable: true}) != relSatisfy {
		t.Fatal("longtext should satisfy mediumtext")
	}
	withDefault := columnSpec{Target: columnForm{
		DataType: "varchar", CharLen: 32, HasDefault: true, DefaultLiteral: "default",
	}}
	other := Column{DataType: "varchar", CharLen: 32, HasDefault: true, DefaultLiteral: "other"}
	if columnRelation(withDefault, other) != relConflict {
		t.Fatal("different defaults should conflict")
	}
	nullable := Column{DataType: "datetime", Nullable: true}
	omitted := columnSpec{Target: columnForm{DataType: "datetime", Nullable: true}}
	if columnRelation(omitted, nullable) != relSatisfy {
		t.Fatal("nullable column without a literal default should satisfy default null")
	}
	signed := columnSpec{Target: columnForm{DataType: "bigint", Unsigned: true, Nullable: true}}
	if columnRelation(signed, Column{DataType: "bigint", Nullable: true, HasNegative: true}) != relConflict {
		t.Fatal("negative values should block unsigned")
	}
	if columnRelation(signed, Column{DataType: "bigint", Nullable: true}) != relSafe {
		t.Fatal("signed bigint without negatives should widen to unsigned")
	}
}

func TestConvergePlans(t *testing.T) {
	spec := mustSpec(t, statusTable)
	table := tableFromSpec(spec)
	harvest := table.Columns["harvest_type"]
	harvest.Nullable = true
	harvest.HasNull = true
	table.Columns["harvest_type"] = harvest
	plan := buildColumnPlan(table, spec, columnByName(spec, "harvest_type"))
	if len(plan.Statements) < 2 || !strings.Contains(plan.Statements[0], "IS NULL") {
		t.Fatal("null backfill should run before modify")
	}
	if strings.Contains(strings.Join(plan.Statements, " "), "ADD COLUMN") {
		t.Fatal("column definition should not add the column")
	}
	agent := table.Columns["agent_id"]
	agent.HasEmpty = true
	table.Columns["agent_id"] = agent
	pk := buildPKPlan(table, spec)
	joined := strings.Join(pk.Statements, " ")
	if strings.Contains(joined, "agent_id") || strings.Contains(joined, "ADD COLUMN") {
		t.Fatal("primary key step should not fill unrelated empties or add columns")
	}
	legacy := tableFromSpec(spec)
	legacy.PK = legacyStatusKey()
	harvest = legacy.Columns["harvest_type"]
	harvest.HasEmpty = true
	legacy.Columns["harvest_type"] = harvest
	pk = buildPKPlan(legacy, spec)
	joined = strings.Join(pk.Statements, " ")
	if !strings.Contains(joined, "harvest_type") || !strings.Contains(joined, "= ''") {
		t.Fatal("emptyAsDefault should fill empty strings on the primary key step")
	}
	if strings.Contains(joined, "ADD COLUMN") || strings.Contains(joined, "DROP INDEX") {
		t.Fatal("status primary key change should not add a column or drop an index")
	}
}

func TestAutoincrementPaths(t *testing.T) {
	spec := mustSpec(t, strategyTableName())
	missing := tableFromSpec(spec)
	delete(missing.Columns, "id")
	missing.PK = []string{"bk_biz_id", "trigger_event_name", "trigger_event_name_reason"}
	add := columnByName(spec, "id").AddSQL
	if !strings.Contains(add, "idx_migrate_id") || !strings.Contains(add, "AUTO_INCREMENT") {
		t.Fatal("missing autoincrement column should add a helper index")
	}
	live := tableFromSpec(spec)
	live.PK = missing.PK
	id := live.Columns["id"]
	id.AutoIncrement = false
	id.Nullable = true
	id.HasNull = true
	live.Columns["id"] = id
	plan := buildColumnPlan(live, spec, columnByName(spec, "id"))
	joined := strings.Join(plan.Statements, " ")
	if !strings.Contains(joined, "IFNULL") || !strings.Contains(plan.Statements[len(plan.Statements)-1], "ADD INDEX") {
		t.Fatal("existing id should assign values and add the helper index in one alter")
	}
	live.Indexes = append(live.Indexes, Index{Name: "idx_user", Columns: []string{"id", "name"}})
	plan = buildColumnPlan(live, spec, columnByName(spec, "id"))
	if strings.Contains(strings.Join(plan.Statements, " "), "idx_migrate_id") {
		t.Fatal("leftmost user index should stay and no helper index should be added")
	}
	keyed := tableFromSpec(spec)
	keyed.PK = []string{"id"}
	pk := buildPKPlan(keyed, spec)
	if strings.Contains(strings.Join(pk.Statements, " "), "DROP INDEX") {
		t.Fatal("single id primary key should not drop an index")
	}
	keyed.Indexes = append(keyed.Indexes, Index{Name: "idx_migrate_id", Columns: []string{"id"}})
	pk = buildPKPlan(keyed, spec)
	if !strings.Contains(strings.Join(pk.Statements, " "), "DROP INDEX `idx_migrate_id`") {
		t.Fatal("helper index should be dropped with the new primary key")
	}
	done := tableFromSpec(spec)
	done.Indexes = append(done.Indexes, Index{Name: "idx_migrate_id", Columns: []string{"id"}})
	present, conflict := targetPKView(done, spec)
	if present || conflict {
		t.Fatal("target primary key should still drop a redundant helper index")
	}
	kept := tableFromSpec(spec)
	kept.PK = []string{"bk_biz_id"}
	kept.Indexes = []Index{{Name: "idx_migrate_id", Columns: []string{"id"}}}
	present, conflict = targetPKView(kept, spec)
	if !present || conflict {
		t.Fatal("helper index should stay when it is the only leftmost index")
	}
	bad := tableFromSpec(spec)
	bad.Indexes = []Index{{Name: "idx_migrate_id", Columns: []string{"name"}, Unique: true}}
	if !helperIndexConflict(bad, columnByName(spec, "id")) {
		t.Fatal("mismatched helper index should conflict")
	}
}

func TestUnfilledPrimaryKeyWritesNothing(t *testing.T) {
	missing := migrated("127.0.0.1:3306", "u1")
	delete(missing.snap.Tables[statusTable].Columns, "machine_id")
	before := missing.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{missing}); err == nil || missing.ddl != before {
		t.Fatal("missing primary key column should write nothing")
	}
	nulls := migrated("127.0.0.1:3306", "u2")
	column := nulls.snap.Tables[statusTable].Columns["machine_id"]
	column.Nullable = true
	column.HasNull = true
	nulls.snap.Tables[statusTable].Columns["machine_id"] = column
	nulls.snap.Tables[statusTable].PK = legacyStatusKey()
	before = nulls.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{nulls}); err == nil || nulls.ddl != before {
		t.Fatal("null primary key column should write nothing")
	}
}

func TestAssignedIDsKeepExistingValues(t *testing.T) {
	allNull := Column{HasNull: true}
	assignMemIDs(&allNull)
	if allNull.MaxID != 1 || allNull.HasNull || !allNull.HasNonNull {
		t.Fatal("all-null ids should start at 1")
	}
	mixed := Column{HasNull: true, HasNonNull: true, NullCount: 2, MaxID: 5}
	assignMemIDs(&mixed)
	if mixed.MaxID != 7 || mixed.HasNull {
		t.Fatal("existing ids should stay and new ids should continue after the max")
	}
}

func TestSchemaConvergenceZeroWrite(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	other := migrated("127.0.0.1:3307", "u2")
	other.snap.Tables[statusTable].PK = []string{"machine_id"}
	before, otherBefore := store.ddl, other.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store, other}); err == nil {
		t.Fatal("unknown primary key should fail precheck")
	}
	if store.ddl != before || other.ddl != otherBefore {
		t.Fatal("failed precheck wrote DDL")
	}
	blocked := migrated("127.0.0.1:3306", "u3")
	id := blocked.snap.Tables["t_db_switching_log"].Columns["id"]
	id.Unsigned = false
	id.HasNegative = true
	blocked.snap.Tables["t_db_switching_log"].Columns["id"] = id
	before = blocked.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{blocked}); err == nil || blocked.ddl != before {
		t.Fatal("negative unsigned conversion should write nothing")
	}
	referenced := migrated("127.0.0.1:3306", "u4")
	referenced.snap.Tables[strategyTableName()].Referenced = true
	referenced.snap.Tables[strategyTableName()].PK = []string{"id"}
	before = referenced.ddl
	if err := run(Options{Type: MigrateTypeSchema}, []Store{referenced}); err == nil || referenced.ddl != before {
		t.Fatal("foreign key reference should write nothing")
	}
}

func TestColumnBackfillFailureDoesNotRecord(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	step := findStep(objectColumnDef, statusTable, "harvest_type", "")
	delete(store.snap.Schema, step.Version)
	column := store.snap.Tables[statusTable].Columns["harvest_type"]
	column.Nullable = true
	column.HasNull = true
	store.snap.Tables[statusTable].Columns["harvest_type"] = column
	store.failAfterFill = true
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("modify failure should fail the step")
	}
	if _, ok := store.snap.Schema[step.Version]; ok {
		t.Fatal("failed column step was recorded")
	}
	if store.snap.Tables[statusTable].Columns["harvest_type"].HasNull {
		t.Fatal("committed null fill should remain")
	}
	if !store.snap.Tables[statusTable].Columns["harvest_type"].Nullable {
		t.Fatal("failed modify should leave the column nullable")
	}
}

func TestDataModeDoesNotChangeSchema(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.snap.Tables[statusTable].PK = legacyStatusKey()
	result := store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"]
	result.DataType = "varchar"
	result.CharLen = 128
	store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"] = result
	ddl := store.ddl
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != ddl || !sameCols(store.snap.Tables[statusTable].PK, legacyStatusKey()) {
		t.Fatal("data mode changed the primary key")
	}
	if store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"].DataType != "varchar" {
		t.Fatal("data mode changed the column definition")
	}
	delete(store.snap.Tables[strategyTableName()].Columns, "deleted_at")
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
		t.Fatal("strategy data should require deleted_at")
	}
}

func TestHistoricalShapeReapplies(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	result := store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"]
	result.DataType = "varchar"
	result.CharLen = 128
	store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"] = result
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	got := store.snap.Tables["t_db_switching_snapshot_log"].Columns["result"]
	if got.DataType != "mediumtext" {
		t.Fatal("recorded column step should widen a historical type again")
	}
}

func TestImplicitSQLTypes(t *testing.T) {
	when, err := implicitSQLType(reflect.TypeOf((*time.Time)(nil)))
	if err != nil || when != "datetime" {
		t.Fatalf("time pointer type: %s, errmsg: %v", when, err)
	}
	event, err := implicitSQLType(reflect.TypeOf(haprobe.DbEventName("")))
	if err != nil || event != "varchar(128)" {
		t.Fatalf("string alias type: %s, errmsg: %v", event, err)
	}
	form, err := parseSQLType("mediumtext")
	if err != nil || !typeEqual(form, Column{DataType: "mediumtext", CharLen: 99}) {
		t.Fatal("mediumtext should compare data type only")
	}
}

func TestInventoryKeyClass(t *testing.T) {
	store := migrated("127.0.0.1:3306", "u1")
	store.snap.Tables[statusTable].PK = legacyStatusKey()
	profiles := inventoryProfiles(store.snap)
	if profiles[0].KeyClass != "legacy" {
		t.Fatalf("key class: %s", profiles[0].KeyClass)
	}
	store.snap.Tables[statusTable].PK = []string{"machine_id"}
	if keyClass(statusSpec(), store.snap.Tables[statusTable].PK) != "conflict" {
		t.Fatal("unknown primary key should be a conflict")
	}
}

func findStep(kind objectKind, table, column, index string) schemaStep {
	for _, step := range schemaSteps() {
		if step.Kind == kind && step.Table == table && step.Column == column && step.Index == index {
			return step
		}
	}
	return schemaStep{}
}

func mustSpec(t *testing.T, name string) tableSpec {
	t.Helper()
	spec, ok := tableByName(name)
	if !ok {
		t.Fatalf("missing table, table: %s", name)
	}
	return spec
}

func exemptPublishedChange(step schemaStep) bool {
	if step.Kind == objectColumnDef || step.Kind == objectPrimaryKey {
		return true
	}
	switch step.Table {
	case "t_db_switching_log", "t_db_switching_snapshot_log", strategyTableName():
		return step.Kind == objectTable
	default:
		return false
	}
}

const publishedStatusCreate = "CREATE TABLE `t_dbha_status` (" +
	"`machine_id` varchar(128) NOT NULL," +
	"`bk_cloud_id` bigint NOT NULL," +
	"`db_ip` varchar(128) NOT NULL," +
	"`db_port` bigint NOT NULL," +
	"`harvest_type` varchar(32) NOT NULL DEFAULT 'default'," +
	"`sequence_id` bigint unsigned NULL," +
	"`agent_id` varchar(128) NULL," +
	"`ips` json NULL," +
	"`message_id` varchar(128) NULL," +
	"`service_id` varchar(128) NULL," +
	"`db_type_name` varchar(128) NULL," +
	"`access_layer` varchar(128) NULL," +
	"`cluster_type` varchar(128) NULL," +
	"`machine_type` varchar(128) NULL," +
	"`instance_role` varchar(128) NULL," +
	"`report_timestamp` bigint unsigned NULL," +
	"`host` json NULL," +
	"`probe` json NULL," +
	"`event` json NULL," +
	"`data` json NULL," +
	"`created_at` datetime NULL," +
	"`updated_at` datetime NULL," +
	"`deleted_at` datetime NULL," +
	"PRIMARY KEY (`machine_id`, `bk_cloud_id`, `db_ip`, `db_port`, `harvest_type`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

const publishedMetadataCreate = "CREATE TABLE `t_dbm_metadata` (" +
	"`bk_cloud_id` bigint NOT NULL," +
	"`ip` varchar(128) NOT NULL," +
	"`port` bigint NOT NULL," +
	"`admin_port` bigint NULL," +
	"`bk_idc_city_id` bigint NULL," +
	"`bk_biz_id` bigint NULL," +
	"`logical_city_id` bigint NULL," +
	"`logcial_city_name` varchar(128) NULL," +
	"`cluster` varchar(128) NULL," +
	"`cluster_id` bigint NULL," +
	"`cluster_type` varchar(128) NULL," +
	"`machine_type` varchar(128) NULL," +
	"`access_layer` varchar(128) NULL," +
	"`status` varchar(128) NULL," +
	"`instance_role` varchar(128) NULL," +
	"`receiver` mediumtext NULL," +
	"`bind_entry` mediumtext NULL," +
	"`proxy_insts` mediumtext NULL," +
	"`binlog_dumpers` mediumtext NULL," +
	"`created_at` datetime NULL," +
	"`updated_at` datetime NULL," +
	"`deleted_at` datetime NULL," +
	"`sync_duration` bigint NULL," +
	"PRIMARY KEY (`bk_cloud_id`, `ip`, `port`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

const publishedSkipCreate = "CREATE TABLE `t_skip_dbinstance` (" +
	"`bk_cloud_id` bigint NOT NULL," +
	"`bk_biz_id` bigint NOT NULL," +
	"`instance_ip` varchar(128) NOT NULL," +
	"`instance_port` bigint NULL," +
	"`created_at` datetime NULL," +
	"`updated_at` datetime NULL," +
	"`deleted_at` datetime NULL," +
	"PRIMARY KEY (`bk_cloud_id`, `bk_biz_id`, `instance_ip`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
