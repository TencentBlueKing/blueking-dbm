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
)

// convergeBatchRows caps the rows one backfill UPDATE touches, so each batch commits quickly.
const convergeBatchRows = 1000

// columnDefView reports whether a column already matches its target definition.
func columnDefView(snap *Snapshot, step schemaStep) (bool, bool) {
	table := snap.Tables[step.Table]
	if table == nil {
		return false, false
	}
	spec, _ := tableByName(step.Table)
	want := columnByName(spec, step.Column)
	live, ok := table.Columns[step.Column]
	if !ok {
		return false, false
	}
	if helperIndexConflict(table, want) {
		return false, true
	}

	switch columnRelation(want, live) {
	case relConflict:
		return false, true
	case relSafe:
		return false, false
	default:
		if keptLiveDefault(want.Target, live) {
			warnKeptDefault(step.Table, want.Name, live.DefaultLiteral)
		}
		return true, false
	}
}

// primaryKeyView reports whether the primary key already matches the baseline.
func primaryKeyView(snap *Snapshot, step schemaStep) (bool, bool) {
	spec, _ := tableByName(step.Table)
	table := snap.Tables[step.Table]
	if table == nil {
		return false, false
	}

	if sameCols(table.PK, spec.Baseline) {
		return targetPKView(table, spec)
	}

	// A legacy key can stay only when nothing blocks rebuilding it.
	if table.Referenced || !historicalPK(spec, table.PK) || pkColumnBlocked(table, spec) {
		return false, true
	}

	return false, false
}

// targetPKView inspects the helper index of an auto-increment primary key.
func targetPKView(table *Table, spec tableSpec) (bool, bool) {
	column, ok := autoColumn(spec)
	if !ok {
		return true, false
	}

	index, found := findIndex(table, helperIndexName(column.Name))
	if !found {
		return true, false
	}
	if index.Unique || index.Primary || !sameCols(index.Columns, []string{column.Name}) {
		return false, true
	}

	// The helper index is still needed while no other index leads with the column.
	if autoLeftmost(table, column.Name, index.Name) {
		return false, false
	}

	return true, false
}

// historicalPK reports whether a primary key is one the model still accepts.
func historicalPK(spec tableSpec, pk []string) bool {
	for _, known := range spec.KnownPKs {
		if sameCols(known, pk) {
			return true
		}
	}

	return false
}

// pkColumnBlocked reports whether baseline columns cannot become the primary key.
func pkColumnBlocked(table *Table, spec tableSpec) bool {
	for _, name := range spec.Baseline {
		column := columnByName(spec, name)
		live, ok := table.Columns[name]
		if !ok {
			allowed := column.Target.AutoIncrement || (column.Target.HasDefault && !column.Target.Nullable)
			if !allowed {
				return true
			}
			continue
		}
		if live.HasNull && !column.Target.AutoIncrement && !column.Target.HasDefault {
			return true
		}
	}

	return false
}

// helperIndexConflict reports whether the helper index exists with the wrong shape.
func helperIndexConflict(table *Table, want columnSpec) bool {
	if !want.Target.AutoIncrement {
		return false
	}

	index, found := findIndex(table, helperIndexName(want.Name))
	if !found {
		return false
	}

	return index.Unique || index.Primary || !sameCols(index.Columns, []string{want.Name})
}

// autoColumn returns the auto-increment primary key column of a spec, if any.
func autoColumn(spec tableSpec) (columnSpec, bool) {
	for _, column := range spec.Columns {
		if column.Primary && column.Target.AutoIncrement {
			return column, true
		}
	}

	return columnSpec{}, false
}

// findIndex returns the named index of a table.
func findIndex(table *Table, name string) (Index, bool) {
	for _, index := range table.Indexes {
		if index.Name == name {
			return index, true
		}
	}

	return Index{}, false
}

// autoLeftmost reports whether a column leads the primary key or another index.
func autoLeftmost(table *Table, column, ignore string) bool {
	if len(table.PK) > 0 && table.PK[0] == column {
		return true
	}

	for _, index := range table.Indexes {
		if index.Name == ignore || index.Primary || len(index.Columns) == 0 {
			continue
		}
		if index.Columns[0] == column {
			return true
		}
	}

	return false
}

// buildColumnPlan plans the statements that converge one column to its target.
func buildColumnPlan(table *Table, spec tableSpec, want columnSpec) convergePlan {
	live := table.Columns[want.Name]
	plan := convergePlan{Table: spec.Name}

	// NULL values must be filled before the column can become NOT NULL.
	if live.HasNull && want.Target.HasDefault {
		plan.FillNull = want.Name
		plan.FillNullSQL = sqlLiteral(want.Target.DefaultLiteral)
		plan.Statements = append(plan.Statements, nullFillSQL(spec.Name, want.Name, plan.FillNullSQL))
	}
	if live.HasNull && want.Target.AutoIncrement {
		plan.AssignColumn = want.Name
		plan.Statements = append(plan.Statements, assignStatements(spec.Name, want.Name, table.PK)...)
	}

	form := modifyForm(want, live)
	statement := "ALTER TABLE `" + spec.Name + "` MODIFY COLUMN " + columnClause(want.Name, form)
	if needHelper(table, want, live) {
		plan.SetIndex = true
		plan.AddIndex = Index{Name: helperIndexName(want.Name), Columns: []string{want.Name}}
		statement += ", ADD INDEX `" + plan.AddIndex.Name + "` (`" + want.Name + "`)"
	}

	plan.Statements = append(plan.Statements, statement)
	plan.SetColumn = true
	plan.ColumnName = want.Name
	plan.Column = form.asColumn(want.Name)

	return plan
}

// modifyForm keeps the wider live type when narrowing would lose data.
func modifyForm(want columnSpec, live Column) columnForm {
	form := want.Target
	if matchesHistorical(want, live) || !widerType(want.Target, live) {
		keepLiveColumnAttrs(&form, want.Target, live)
		return form
	}

	form.DataType = live.DataType
	form.CharLen = live.CharLen
	if !want.Target.Unsigned {
		form.Unsigned = live.Unsigned
	}
	keepLiveColumnAttrs(&form, want.Target, live)

	return form
}

// keepLiveColumnAttrs carries live presentation attributes over to the new form.
func keepLiveColumnAttrs(form *columnForm, want columnForm, live Column) {
	form.Charset = live.Charset
	form.Collation = live.Collation
	form.Comment = live.Comment

	if timeType(want.DataType) && timeType(live.DataType) {
		form.DataType = live.DataType
	}
	if keptLiveDefault(want, live) {
		form.HasDefault = true
		form.DefaultLiteral = live.DefaultLiteral
	}
	if form.OnUpdate == "" && !want.ExplicitNull && currentTimestamp(live.OnUpdate) {
		form.OnUpdate = live.OnUpdate
	}
}

// needHelper reports whether an auto-increment column still needs its helper index.
func needHelper(table *Table, want columnSpec, live Column) bool {
	if !want.Target.AutoIncrement || live.AutoIncrement || autoLeftmost(table, want.Name, "") {
		return false
	}

	_, found := findIndex(table, helperIndexName(want.Name))

	return !found
}

// buildPKPlan plans the statements that converge a primary key to the baseline.
func buildPKPlan(table *Table, spec tableSpec) convergePlan {
	plan := convergePlan{Table: spec.Name}

	// Key is already right: only the leftover helper index has to go.
	if sameCols(table.PK, spec.Baseline) {
		column, ok := autoColumn(spec)
		if !ok {
			return convergePlan{}
		}
		plan.DropIndex = helperIndexName(column.Name)
		plan.Statements = []string{dropIndexSQL(spec.Name, plan.DropIndex)}
		return plan
	}

	plan.Statements = append(plan.Statements, emptyFills(table, spec, &plan)...)
	drop := pkDropIndex(table, spec)
	plan.DropIndex = drop
	plan.SetPK = true
	plan.PK = append([]string{}, spec.Baseline...)
	plan.Statements = append(plan.Statements, pkAlterSQL(spec.Name, spec.Baseline, drop))

	return plan
}

// emptyFills fills empty strings in baseline columns that treat empty as default.
func emptyFills(table *Table, spec tableSpec, plan *convergePlan) []string {
	var statements []string
	for _, name := range spec.Baseline {
		column := columnByName(spec, name)
		live, ok := table.Columns[name]
		if !ok || !column.EmptyAsDefault || !live.HasEmpty {
			continue
		}
		plan.FillEmpty = name
		plan.FillEmptySQL = sqlLiteral(column.Target.DefaultLiteral)
		statements = append(statements, emptyFillSQL(spec.Name, name, plan.FillEmptySQL))
	}

	return statements
}

// pkDropIndex returns the helper index to drop together with the primary key.
func pkDropIndex(table *Table, spec tableSpec) string {
	column, ok := autoColumn(spec)
	if !ok || len(spec.Baseline) == 0 || spec.Baseline[0] != column.Name {
		return ""
	}

	index, found := findIndex(table, helperIndexName(column.Name))
	if !found || index.Unique || index.Primary || !sameCols(index.Columns, []string{column.Name}) {
		return ""
	}

	return index.Name
}

// sqlLiteral quotes a literal for inline SQL.
func sqlLiteral(value string) string {
	return "'" + strings.ReplaceAll(value, "'", "''") + "'"
}

// nullFillSQL renders the batched UPDATE that backfills NULL values.
func nullFillSQL(table, column, literal string) string {
	return fmt.Sprintf(
		"UPDATE `%s` SET `%s` = %s WHERE `%s` IS NULL LIMIT %d",
		table, column, literal, column, convergeBatchRows,
	)
}

// emptyFillSQL renders the batched UPDATE that backfills empty-string values.
func emptyFillSQL(table, column, literal string) string {
	return fmt.Sprintf(
		"UPDATE `%s` SET `%s` = %s WHERE `%s` = '' LIMIT %d",
		table, column, literal, column, convergeBatchRows,
	)
}

// assignStatements renders the batched UPDATE that assigns ids to NULL auto-increment values.
// The user-variable assignment is deprecated in MySQL 8.0 (warning 1287), but 5.7 has no
// window functions, so it stays. The session variable survives between batches on the pinned connection.
func assignStatements(table, column string, pk []string) []string {
	set := fmt.Sprintf(
		"SET @dbha_migrate_n := IFNULL((SELECT MAX(`%s`) FROM `%s`), 0)", column, table,
	)
	update := fmt.Sprintf(
		"UPDATE `%s` SET `%s` = (@dbha_migrate_n := @dbha_migrate_n + 1) WHERE `%s` IS NULL%s LIMIT %d",
		table, column, column, orderBy(pk), convergeBatchRows,
	)

	return []string{set, update}
}

// orderBy renders an ORDER BY clause for deterministic id assignment.
func orderBy(pk []string) string {
	if len(pk) == 0 {
		return ""
	}

	parts := make([]string, 0, len(pk))
	for _, name := range pk {
		parts = append(parts, "`"+name+"`")
	}

	return " ORDER BY " + strings.Join(parts, ", ")
}

// dropIndexSQL renders the ALTER TABLE that drops one index.
func dropIndexSQL(table, name string) string {
	return "ALTER TABLE `" + table + "` DROP INDEX `" + name + "`"
}

// pkAlterSQL renders the ALTER TABLE that rebuilds the primary key.
func pkAlterSQL(table string, columns []string, dropIndex string) string {
	keys := make([]string, 0, len(columns))
	for _, name := range columns {
		keys = append(keys, "`"+name+"`")
	}

	statement := "ALTER TABLE `" + table + "` DROP PRIMARY KEY, ADD PRIMARY KEY (" +
		strings.Join(keys, ", ") + ")"
	if dropIndex != "" {
		statement += ", DROP INDEX `" + dropIndex + "`"
	}

	return statement
}
