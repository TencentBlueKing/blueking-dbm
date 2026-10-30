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
	"sort"
	"strings"
	"sync"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	"gorm.io/gorm/schema"
)

func TestCatalogKeepsModelColumnContract(t *testing.T) {
	for _, model := range managedModels() {
		name := model.(interface{ TableName() string }).TableName()
		spec, ok := tableByName(name)
		if !ok {
			t.Fatalf("catalog missing table, table: %s", name)
		}
		assertGormContract(t, model, spec)
		for _, key := range spec.KnownPKs {
			if sameCols(key, spec.Baseline) {
				t.Fatalf("historical primary key repeats the target, table: %s", name)
			}
		}
	}

	meta, _ := tableByName(hamodel.DbmMetadataTableName)
	if !catalogHasColumn(meta, "logcial_city_name") {
		t.Fatal("historical column logcial_city_name was renamed")
	}
	skip, _ := tableByName(hamodel.SkipDbInstanceTableName)
	if sameCols(skip.Baseline, []string{"bk_cloud_id", "bk_biz_id", "instance_ip", "instance_port"}) {
		t.Fatal("instance_port was added to the skip-instance primary key")
	}
}

func TestCatalogCoversEveryManagedModel(t *testing.T) {
	models := managedModels()
	tables := modelTables()
	if len(tables) != len(models) {
		t.Fatalf("catalog and model list differ, tables: %d, models: %d", len(tables), len(models))
	}
	for i, model := range models {
		if name := model.(interface{ TableName() string }).TableName(); tables[i].Name != name {
			t.Fatalf("catalog order differs from model list, position: %d, table: %s", i, name)
		}
	}
}

func TestLedgerModelsKeepGormContract(t *testing.T) {
	schemaSpec, dataSpec := mustLedgerSpecs(t)
	assertGormContract(t, schemaLedgerRow{}, schemaSpec)
	assertGormContract(t, dataLedgerRow{}, dataSpec)
}

func mustLedgerSpecs(t *testing.T) (tableSpec, tableSpec) {
	t.Helper()
	schemaSpec, dataSpec, err := ledgerSpecs()
	if err != nil {
		t.Fatalf("reflect ledger models failed, errmsg: %s", err)
	}

	return schemaSpec, dataSpec
}

func TestLedgerTablesStayUnmanaged(t *testing.T) {
	for _, step := range schemaSteps() {
		if step.Table == schemaLedgerTable || step.Table == dataLedgerTable {
			t.Fatalf("ledger table got a schema step, table: %s, version: %d", step.Table, step.Version)
		}
	}
}

// The frozen ledger CREATE statements must declare exactly what the ledger models declare.
func TestFrozenLedgerCreateMatchesModel(t *testing.T) {
	schemaSpec, dataSpec := mustLedgerSpecs(t)
	for _, item := range []struct {
		create string
		spec   tableSpec
	}{{schemaLedgerSQL, schemaSpec}, {dataLedgerSQL, dataSpec}} {
		if want := frozenLedgerCreate(item.spec); item.create != want {
			t.Fatalf("frozen ledger create drifted from model, table: %s, want: %s", item.spec.Name, want)
		}
	}
}

func TestStrategyFieldConstantsMatchModel(t *testing.T) {
	parsed := parseGormModel(t, hamodel.DbSwitchingStrategy{})
	fields := []string{
		hamodel.DbSwitchingStrategyFieldID,
		hamodel.DbSwitchingStrategyFieldName,
		hamodel.DbSwitchingStrategyFieldBkBizID,
		hamodel.DbSwitchingStrategyFieldStatus,
		hamodel.DbSwitchingStrategyFieldTriggerEventName,
		hamodel.DbSwitchingStrategyFieldTriggerEventNameReason,
		hamodel.DbSwitchingStrategyFieldTriggerCount,
		hamodel.DbSwitchingStrategyFieldPriority,
		hamodel.DbSwitchingStrategyFieldScope,
		hamodel.DbSwitchingStrategyFieldAction,
		hamodel.DbSwitchingStrategyFieldDescription,
		hamodel.DbSwitchingStrategyFieldCreatedAt,
		hamodel.DbSwitchingStrategyFieldUpdatedAt,
		hamodel.DbSwitchingStrategyFieldDeletedAt,
	}
	for _, field := range fields {
		if parsed.LookUpField(field) == nil {
			t.Fatalf("strategy field constant has no model column, column: %s", field)
		}
	}
}

// Every non auto-increment model column gates the data step; the auto-increment id does not,
// because historical strategy tables were keyed without it.
func TestStrategyReadyFollowsModelColumns(t *testing.T) {
	spec, _ := tableByName(hamodel.DbSwitchingStrategyTableName)
	ready := &Snapshot{Tables: map[string]*Table{spec.Name: liveTableFrom(spec)}}
	if !strategyReady(ready) {
		t.Fatal("strategy table built from the model is not ready")
	}

	for _, column := range spec.Columns {
		table := liveTableFrom(spec)
		delete(table.Columns, column.Name)
		snap := &Snapshot{Tables: map[string]*Table{spec.Name: table}}
		if column.Target.AutoIncrement {
			if !strategyReady(snap) {
				t.Fatalf("missing auto-increment column blocked the data step, column: %s", column.Name)
			}
			continue
		}
		if strategyReady(snap) {
			t.Fatalf("missing model column did not block the data step, column: %s", column.Name)
		}
	}
}

func TestLedgerShapeFollowsModel(t *testing.T) {
	schemaSpec, dataSpec := mustLedgerSpecs(t)
	for _, spec := range []tableSpec{schemaSpec, dataSpec} {
		if !ledgerShape(liveTableFrom(spec), spec) {
			t.Fatalf("ledger built from the model is unhealthy, table: %s", spec.Name)
		}
		for _, column := range spec.Columns {
			table := liveTableFrom(spec)
			delete(table.Columns, column.Name)
			if ledgerShape(table, spec) {
				t.Fatalf("ledger missing a column passed, table: %s, column: %s", spec.Name, column.Name)
			}
		}
		table := liveTableFrom(spec)
		table.Indexes = nil
		if ledgerShape(table, spec) {
			t.Fatalf("ledger missing its unique index passed, table: %s", spec.Name)
		}
	}
}

// assertGormContract checks that GORM and the migrator reflector see the same columns,
// primary key and indexes for one model.
func assertGormContract(t *testing.T, model any, spec tableSpec) {
	t.Helper()

	parsed := parseGormModel(t, model)
	reflected := make([]string, 0, len(spec.Columns))
	for _, column := range spec.Columns {
		reflected = append(reflected, column.Name)
	}
	if !sameSet(parsed.DBNames, reflected) {
		t.Fatalf("columns differ from gorm, table: %s, gorm: %s, catalog: %s",
			spec.Name, strings.Join(parsed.DBNames, ","), strings.Join(reflected, ","))
	}
	if !sameCols(spec.Baseline, parsed.PrimaryFieldDBNames) {
		t.Fatalf("baseline differs from gorm primary key, table: %s, baseline: %s, primary_key: %s",
			spec.Name, strings.Join(spec.Baseline, ","), strings.Join(parsed.PrimaryFieldDBNames, ","))
	}

	indexes := parsed.ParseIndexes()
	if len(indexes) != len(spec.Indexes) {
		t.Fatalf("index count differs from gorm, table: %s, gorm: %d, catalog: %d",
			spec.Name, len(indexes), len(spec.Indexes))
	}
	for _, index := range indexes {
		if !catalogHasGormIndex(spec, index) {
			t.Fatalf("catalog missing gorm index, table: %s, index: %s", spec.Name, index.Name)
		}
	}
}

func parseGormModel(t *testing.T, model any) *schema.Schema {
	t.Helper()

	parsed, err := schema.Parse(model, &sync.Map{}, schema.NamingStrategy{})
	if err != nil {
		t.Fatalf("gorm parse failed, errmsg: %s", err)
	}

	return parsed
}

func catalogHasGormIndex(spec tableSpec, want *schema.Index) bool {
	columns := make([]string, 0, len(want.Fields))
	prefix := make([]int, 0, len(want.Fields))
	for _, field := range want.Fields {
		columns = append(columns, field.DBName)
		prefix = append(prefix, field.Length)
	}

	for _, index := range spec.Indexes {
		if index.Name != want.Name || index.Unique != (want.Class == "UNIQUE") {
			continue
		}
		if sameCols(index.Columns, columns) && samePrefix(index.Prefix, prefix) {
			return true
		}
	}

	return false
}

func catalogHasColumn(spec tableSpec, name string) bool {
	for _, column := range spec.Columns {
		if column.Name == name {
			return true
		}
	}
	return false
}

// frozenLedgerCreate renders the CREATE statement a ledger model implies, in the frozen layout:
// columns, primary key, then inline keys.
func frozenLedgerCreate(spec tableSpec) string {
	parts := make([]string, 0, len(spec.Columns)+len(spec.Indexes)+1)
	for _, column := range spec.Columns {
		parts = append(parts, columnClause(column.Name, column.Target))
	}
	keys := make([]string, 0, len(spec.Baseline))
	for _, name := range spec.Baseline {
		keys = append(keys, "`"+name+"`")
	}
	parts = append(parts, "PRIMARY KEY ("+strings.Join(keys, ", ")+")")
	for _, index := range spec.Indexes {
		columns := make([]string, 0, len(index.Columns))
		for _, name := range index.Columns {
			columns = append(columns, "`"+name+"`")
		}
		kind := "KEY"
		if index.Unique {
			kind = "UNIQUE KEY"
		}
		parts = append(parts, kind+" `"+index.Name+"` ("+strings.Join(columns, ", ")+")")
	}

	return "CREATE TABLE `" + spec.Name + "` (" + strings.Join(parts, ",") + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
}

// liveTableFrom builds the live table a fully migrated database would report for spec.
func liveTableFrom(spec tableSpec) *Table {
	table := &Table{Columns: map[string]Column{}, PK: append([]string{}, spec.Baseline...)}
	for _, column := range spec.Columns {
		table.Columns[column.Name] = Column{Name: column.Name, DataType: column.Target.DataType}
	}
	for _, index := range spec.Indexes {
		table.Indexes = append(table.Indexes, Index{
			Name: index.Name, Unique: index.Unique, Columns: index.Columns, Prefix: index.Prefix,
		})
	}

	return table
}

func sameSet(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	a := append([]string{}, left...)
	b := append([]string{}, right...)
	sort.Strings(a)
	sort.Strings(b)

	return sameCols(a, b)
}

func samePrefix(left, right []int) bool {
	for i := 0; i < len(left) || i < len(right); i++ {
		if prefixAt(left, i) != prefixAt(right, i) {
			return false
		}
	}
	return true
}
