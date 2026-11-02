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
	"context"
	"database/sql"
	"fmt"
	"strings"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// duplicateSampleLimit caps the duplicate key groups one probe reads and logs.
const duplicateSampleLimit = 5

// keyExpr is one key column of a duplicate probe and how its value is grouped.
// SkipNull drops rows whose column is NULL. Default, when set, is the SQL literal NULL values
// (and empty strings when EmptyAsDefault) are grouped as, matching the converge backfill.
type keyExpr struct {
	Column         string
	SkipNull       bool
	Default        string
	EmptyAsDefault bool
}

// duplicateSample is one duplicated key value set and how many rows share it.
type duplicateSample struct {
	Values []string
	Rows   int64
}

// DuplicateSamples returns up to limit key value sets that more than one row of table shares.
func (s *mysqlStore) DuplicateSamples(table string, keys []keyExpr, limit int) ([]duplicateSample, error) {
	query, err := duplicateSQL(table, keys, limit)
	if err != nil {
		return nil, err
	}

	rows, err := s.conn.QueryContext(context.Background(), query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var samples []duplicateSample
	for rows.Next() {
		values := make([]sql.NullString, len(keys))
		targets := make([]any, 0, len(keys)+1)
		for i := range values {
			targets = append(targets, &values[i])
		}
		var count int64
		targets = append(targets, &count)
		if err = rows.Scan(targets...); err != nil {
			return nil, err
		}
		samples = append(samples, duplicateSample{Values: sampleValues(values), Rows: count})
	}

	return samples, rows.Err()
}

// TableNonEmpty reports whether a table has at least one row.
func (s *mysqlStore) TableNonEmpty(table string) (bool, error) {
	name, err := quotedIdent(table)
	if err != nil {
		return false, err
	}

	var one int
	err = s.conn.QueryRowContext(context.Background(), "SELECT 1 FROM "+name+" LIMIT 1").Scan(&one)
	if err == sql.ErrNoRows {
		return false, nil
	}

	return err == nil, err
}

// duplicateSQL builds the GROUP BY probe that reads duplicate key value sets.
func duplicateSQL(table string, keys []keyExpr, limit int) (string, error) {
	name, err := quotedIdent(table)
	if err != nil {
		return "", err
	}
	if len(keys) == 0 {
		return "", fmt.Errorf("duplicate probe needs columns, table: %s", table)
	}
	if limit <= 0 {
		limit = 1
	}

	parts := make([]string, 0, len(keys))
	filters := make([]string, 0, len(keys))
	for _, key := range keys {
		quoted, err := quotedIdent(key.Column)
		if err != nil {
			return "", err
		}
		parts = append(parts, groupExpr(quoted, key))
		if key.SkipNull {
			filters = append(filters, quoted+" IS NOT NULL")
		}
	}

	group := strings.Join(parts, ", ")
	query := "SELECT " + group + ", COUNT(*) FROM " + name
	if len(filters) > 0 {
		query += " WHERE " + strings.Join(filters, " AND ")
	}
	query += fmt.Sprintf(" GROUP BY %s HAVING COUNT(*) > 1 LIMIT %d", group, limit)

	return query, nil
}

// groupExpr renders the value a key column is grouped by.
func groupExpr(quoted string, key keyExpr) string {
	if key.Default == "" {
		return quoted
	}

	value := quoted
	if key.EmptyAsDefault {
		value = "NULLIF(" + quoted + ", '')"
	}

	return "COALESCE(" + value + ", " + key.Default + ")"
}

// sampleValues renders scanned key values for logs; NULL renders as NULL.
func sampleValues(values []sql.NullString) []string {
	out := make([]string, 0, len(values))
	for _, value := range values {
		if !value.Valid {
			out = append(out, "NULL")
			continue
		}
		out = append(out, value.String)
	}

	return out
}

// quotedIdent quotes an identifier, refusing anything that could escape it.
func quotedIdent(name string) (string, error) {
	if name == "" || strings.ContainsAny(name, "`;\\") {
		return "", fmt.Errorf("invalid identifier, name: %s", name)
	}

	return "`" + name + "`", nil
}

// probeStepData fills the facts schema steps need: row presence and duplicate keys.
func probeStepData(store Store, snap *Snapshot) error {
	if snap == nil || !snap.Database {
		return nil
	}
	if snap.NonEmpty == nil {
		snap.NonEmpty = map[string]bool{}
	}
	if snap.DuplicateKeys == nil {
		snap.DuplicateKeys = map[string]bool{}
	}

	for _, spec := range modelTables() {
		live := snap.Tables[spec.Name]
		if live == nil {
			continue
		}

		nonEmpty, err := store.TableNonEmpty(spec.Name)
		if err != nil {
			return err
		}
		snap.NonEmpty[spec.Name] = nonEmpty

		if err := probeUniqueDuplicates(store, snap, spec, live); err != nil {
			return err
		}
		if err := probePrimaryKeyDuplicates(store, snap, spec, live); err != nil {
			return err
		}
	}

	return nil
}

// probeUniqueDuplicates marks unique indexes that duplicate rows would block.
func probeUniqueDuplicates(store Store, snap *Snapshot, spec tableSpec, live *Table) error {
	for _, index := range spec.Indexes {
		if err := probeIndexDuplicates(store, snap, spec, live, index); err != nil {
			return err
		}
	}

	return nil
}

// probeIndexDuplicates marks one unique index that duplicate rows would block.
func probeIndexDuplicates(store Store, snap *Snapshot, spec tableSpec, live *Table, index indexSpec) error {
	if !index.Unique {
		return nil
	}

	// An index that exists already, or whose columns are missing, needs no probe.
	present, _ := matchIndex(live.Indexes, index)
	if present || !columnsPresent(live, index.Columns) {
		return nil
	}

	nullable := nullableColumns(live, index.Columns)
	keys := make([]keyExpr, 0, len(index.Columns))
	for i, column := range index.Columns {
		keys = append(keys, keyExpr{Column: column, SkipNull: nullable[i]})
	}
	samples, err := store.DuplicateSamples(spec.Name, keys, duplicateSampleLimit)
	if err != nil {
		return err
	}
	if len(samples) == 0 {
		return nil
	}

	snap.DuplicateKeys[indexDuplicateKey(spec.Name, index.Name)] = true
	for _, sample := range samples {
		logger.Warn("unique index duplicate, table: %s, index: %s, columns: %s, key: %s, rows: %d",
			spec.Name, index.Name, strings.Join(index.Columns, ", "), strings.Join(sample.Values, ", "), sample.Rows)
	}

	return nil
}

// probePrimaryKeyDuplicates marks a primary key rebuild that duplicate rows would block.
// Values are grouped as the converge backfill will leave them, so the probe sees the final keys.
func probePrimaryKeyDuplicates(store Store, snap *Snapshot, spec tableSpec, live *Table) error {
	if !pkProbeNeeded(spec, live) {
		return nil
	}

	keys := make([]keyExpr, 0, len(spec.Baseline))
	for _, name := range spec.Baseline {
		keys = append(keys, pkKeyExpr(columnByName(spec, name), live.Columns[name]))
	}
	samples, err := store.DuplicateSamples(spec.Name, keys, duplicateSampleLimit)
	if err != nil {
		return err
	}
	if len(samples) == 0 {
		return nil
	}

	snap.DuplicateKeys[primaryDuplicateKey(spec.Name)] = true
	for _, sample := range samples {
		logger.Warn("primary key duplicate, table: %s, columns: %s, key: %s, rows: %d",
			spec.Name, strings.Join(spec.Baseline, ", "), strings.Join(sample.Values, ", "), sample.Rows)
	}

	return nil
}

// pkProbeNeeded reports whether rebuilding the live primary key could hit duplicate rows.
// A legacy key whose columns all stay in the baseline, with values the backfill never rewrites,
// keeps every row unique, so the full-table GROUP BY is skipped.
func pkProbeNeeded(spec tableSpec, live *Table) bool {
	if live == nil || len(spec.Baseline) == 0 || sameCols(live.PK, spec.Baseline) {
		return false
	}
	if !historicalPK(spec, live.PK) || !columnsPresent(live, spec.Baseline) {
		return false
	}

	return !uniqueKeyKept(spec, live.PK)
}

// uniqueKeyKept reports whether every column of a live unique key stays in the baseline unchanged.
func uniqueKeyKept(spec tableSpec, key []string) bool {
	if len(key) == 0 {
		return false
	}
	for _, name := range key {
		if !containsColumn(spec.Baseline, name) || columnByName(spec, name).EmptyAsDefault {
			return false
		}
	}

	return true
}

// pkKeyExpr groups one baseline column by the value it holds once converged.
func pkKeyExpr(want columnSpec, live Column) keyExpr {
	switch {
	case want.Target.AutoIncrement:
		return keyExpr{Column: want.Name, SkipNull: true}
	case want.Target.HasDefault:
		return keyExpr{
			Column: want.Name, Default: sqlLiteral(want.Target.DefaultLiteral), EmptyAsDefault: want.EmptyAsDefault,
		}
	default:
		return keyExpr{Column: want.Name, SkipNull: live.Nullable}
	}
}

// containsColumn reports whether a column list names a column.
func containsColumn(columns []string, name string) bool {
	for _, column := range columns {
		if column == name {
			return true
		}
	}

	return false
}

// indexDuplicateKey is the DuplicateKeys entry of a unique index.
func indexDuplicateKey(table, index string) string {
	return table + "\x00" + index
}

// primaryDuplicateKey is the DuplicateKeys entry of a primary key rebuild.
func primaryDuplicateKey(table string) string {
	return table + "\x00" + "PRIMARY"
}

// nullableColumns reports, per column, whether it accepts NULL.
func nullableColumns(table *Table, columns []string) []bool {
	nullable := make([]bool, len(columns))
	if table == nil {
		return nullable
	}

	for i, name := range columns {
		column, ok := table.Columns[name]
		nullable[i] = ok && column.Nullable
	}

	return nullable
}

// columnsPresent reports whether every named column exists on the table.
func columnsPresent(table *Table, columns []string) bool {
	for _, name := range columns {
		if _, ok := table.Columns[name]; !ok {
			return false
		}
	}

	return true
}
