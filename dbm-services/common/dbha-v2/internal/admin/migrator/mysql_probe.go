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
)

// HasDuplicate reports whether a table already has duplicate values for columns.
func (s *mysqlStore) HasDuplicate(table string, columns []string, nullable []bool) (bool, error) {
	query, err := duplicateSQL(table, columns, nullable)
	if err != nil {
		return false, err
	}

	var one int
	err = s.conn.QueryRowContext(context.Background(), query).Scan(&one)
	if err == sql.ErrNoRows {
		return false, nil
	}

	return err == nil, err
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

// duplicateSQL builds the GROUP BY probe that detects duplicate keys.
func duplicateSQL(table string, columns []string, nullable []bool) (string, error) {
	name, err := quotedIdent(table)
	if err != nil {
		return "", err
	}

	parts := make([]string, 0, len(columns))
	filters := make([]string, 0, len(columns))
	for i, column := range columns {
		quoted, err := quotedIdent(column)
		if err != nil {
			return "", err
		}
		parts = append(parts, quoted)
		if i < len(nullable) && nullable[i] {
			filters = append(filters, quoted+" IS NOT NULL")
		}
	}
	if len(parts) == 0 {
		return "", fmt.Errorf("duplicate probe needs columns, table: %s", table)
	}

	query := "SELECT 1 FROM " + name
	if len(filters) > 0 {
		query += " WHERE " + strings.Join(filters, " AND ")
	}
	query += " GROUP BY " + strings.Join(parts, ", ") + " HAVING COUNT(*) > 1 LIMIT 1"

	return query, nil
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
	}

	return nil
}

// probeUniqueDuplicates marks unique indexes that duplicate rows would block.
func probeUniqueDuplicates(store Store, snap *Snapshot, spec tableSpec, live *Table) error {
	for _, index := range spec.Indexes {
		if !index.Unique {
			continue
		}

		// An index that exists already, or whose columns are missing, needs no probe.
		present, _ := matchIndex(live.Indexes, index)
		if present || !columnsPresent(live, index.Columns) {
			continue
		}

		duplicate, err := store.HasDuplicate(spec.Name, index.Columns, nullableColumns(live, index.Columns))
		if err != nil {
			return err
		}
		if duplicate {
			snap.DuplicateKeys[spec.Name+"\x00"+index.Name] = true
		}
	}

	return nil
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
