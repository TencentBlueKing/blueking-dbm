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
	"strings"
	"testing"
)

func TestMariaDBStringDefaultsAreUnquoted(t *testing.T) {
	if !mariaDB("10.6.12-MariaDB-log") || mariaDB("8.0.36") {
		t.Fatal("server flavor detection changed")
	}

	cases := map[string]string{
		"'default'":           "default",
		"'don''t'":            "don't",
		"'NULL'":              "NULL",
		"''":                  "",
		"0":                   "0",
		"current_timestamp()": "current_timestamp()",
		"'":                   "'",
	}
	for raw, want := range cases {
		if got := unquoteLiteral(raw); got != want {
			t.Fatalf("unquote literal, raw: %s, got: %s, want: %s", raw, got, want)
		}
	}
}

func TestMariaDBQuotedDefaultSatisfiesModel(t *testing.T) {
	status, _ := tableByName(statusTable)
	harvest := columnByName(status, "harvest_type")

	live := mariaLiveColumn("'default'")
	if columnRelation(harvest, live) != relSatisfy {
		t.Fatal("mariadb quoted default should satisfy the model default")
	}
	if columnRelation(harvest, mariaLiveColumn("'other'")) != relConflict {
		t.Fatal("a different mariadb default must still conflict")
	}

	// MySQL keeps the raw value, so a literal that really contains quotes stays as is.
	raw := liveColumn(
		"harvest_type", "varchar", "NO", "varchar(32)", "", sql.NullInt64{Int64: 32, Valid: true},
		sql.NullString{String: "'default'", Valid: true}, sql.NullString{}, sql.NullString{}, sql.NullString{},
	)
	if raw.DefaultLiteral != "'default'" || columnRelation(harvest, raw) != relConflict {
		t.Fatalf("mysql default must not be unquoted, default: %s", raw.DefaultLiteral)
	}
}

// mariaLiveColumn mimics loadColumns on MariaDB for the status harvest_type column.
func mariaLiveColumn(columnDefault string) Column {
	column := liveColumn(
		"harvest_type", "varchar", "NO", "varchar(32)", "", sql.NullInt64{Int64: 32, Valid: true},
		sql.NullString{String: columnDefault, Valid: true}, sql.NullString{}, sql.NullString{}, sql.NullString{},
	)
	if column.HasDefault {
		column.DefaultLiteral = unquoteLiteral(column.DefaultLiteral)
	}

	return column
}

func TestHistoricalPrimaryKeyKeepsFrozenCreate(t *testing.T) {
	spec, _ := tableByName(statusTable)
	spec.Columns = append([]columnSpec{}, spec.Columns...)
	for i := range spec.Columns {
		if spec.Columns[i].Name == "machine_id" {
			spec.Columns[i].Historical = "varchar(128)"
			spec.Columns[i].Target.CharLen = 255
		}
	}

	columns := publishedColumns()
	checked := 0
	for _, step := range publishedSchemaSteps() {
		if step.Table != spec.Name || (step.Kind != objectTable && step.Column != "machine_id") {
			continue
		}
		if step.Kind == objectColumnDef {
			continue
		}
		want, ok := expectedPublishedApply(spec, step, columns)
		if !ok || want != step.Apply {
			t.Fatalf("historical primary key changed published apply, version: %d", step.Version)
		}
		checked++
	}
	if checked != 2 {
		t.Fatalf("expected create and add steps, checked: %d", checked)
	}

	create, _ := frozenCreate(spec.Name)
	clause, ok := createColumnClause(create, "machine_id")
	if !ok || clause != "`machine_id` varchar(128) NOT NULL" {
		t.Fatalf("frozen create clause, clause: %s", clause)
	}
}

func TestCreateColumnClauseStaysInsideCreate(t *testing.T) {
	create, ok := frozenCreate("t_db_switching_snapshot_log")
	if !ok {
		t.Fatal("snapshot table create is not published")
	}

	clause, ok := createColumnClause(create, "id")
	if !ok || clause != "`id` bigint unsigned NOT NULL AUTO_INCREMENT" {
		t.Fatalf("auto increment clause leaked, clause: %s", clause)
	}
	if clause, ok = createColumnClause(create, "finished_time"); !ok || clause != "`finished_time` datetime NULL" {
		t.Fatalf("last column clause, clause: %s", clause)
	}
	if _, ok = createColumnClause(create, "missing"); ok {
		t.Fatal("missing column must not be found")
	}
}

func TestUnpublishedHistoricalTableUsesTarget(t *testing.T) {
	spec := tableSpec{
		Name:     "t_dbha_unpublished",
		Baseline: []string{"id"},
		Columns: []columnSpec{
			{Name: "id", Target: columnForm{DataType: "bigint"}},
			{Name: "result", Historical: "varchar(128)", Target: columnForm{DataType: "mediumtext", Nullable: true}},
		},
	}
	if _, ok := publishedCreateSQL(spec); ok {
		t.Fatal("unpublished table must fail published validation")
	}

	create := createSQL(spec)
	if !strings.Contains(create, "`result` mediumtext NULL") || !strings.HasPrefix(create, "CREATE TABLE") {
		t.Fatalf("unpublished create must use the target, create: %s", create)
	}
}

func TestExplicitNullDropsLiveTimeAttributes(t *testing.T) {
	spec, _ := tableByName(strategyTableName())
	deleted := columnByName(spec, "deleted_at")
	if !deleted.Target.ExplicitNull || deleted.Target.HasDefault {
		t.Fatal("deleted_at must keep the explicit null default")
	}

	withDefault := Column{
		Name: "deleted_at", DataType: "datetime", Nullable: true, HasDefault: true, DefaultLiteral: "CURRENT_TIMESTAMP",
	}
	onUpdate := Column{Name: "deleted_at", DataType: "datetime", Nullable: true, OnUpdate: "CURRENT_TIMESTAMP"}
	for _, live := range []Column{withDefault, onUpdate} {
		if columnRelation(deleted, live) != relSafe {
			t.Fatalf("explicit null should converge, live: %+v", live)
		}
		form := modifyForm(deleted, live)
		clause := columnClause("deleted_at", form)
		if strings.Contains(clause, "DEFAULT") || strings.Contains(clause, "ON UPDATE") {
			t.Fatalf("modify keeps live time attributes, clause: %s", clause)
		}
		if columnRelation(deleted, form.asColumn("deleted_at")) != relSatisfy {
			t.Fatalf("converged column does not satisfy the model, clause: %s", clause)
		}
	}

	notNull := withDefault
	notNull.Nullable = false
	if columnRelation(deleted, notNull) != relConflict {
		t.Fatal("explicit null on a not null column must conflict")
	}
	literal := Column{Name: "deleted_at", DataType: "datetime", Nullable: true, HasDefault: true, DefaultLiteral: "x"}
	if columnRelation(deleted, literal) != relConflict {
		t.Fatal("explicit null with a literal default must conflict")
	}

	created := columnByName(spec, "created_at")
	if created.Target.ExplicitNull || columnRelation(created, withDefault) != relSatisfy {
		t.Fatal("undeclared time default must still be kept")
	}
}
