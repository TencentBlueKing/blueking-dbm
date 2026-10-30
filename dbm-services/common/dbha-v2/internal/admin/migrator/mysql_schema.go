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
	"strings"
)

// loadTables reads columns, indexes, and foreign-key references of the given tables.
func (s *mysqlStore) loadTables(snap *Snapshot, tables []string) error {
	if err := s.loadColumns(snap, tables); err != nil {
		return err
	}
	if err := s.loadIndexes(snap, tables); err != nil {
		return err
	}

	return s.loadReferences(snap, tables)
}

// loadColumns reads every column of the given tables from information_schema.
func (s *mysqlStore) loadColumns(snap *Snapshot, tables []string) error {
	query, args := schemaFilter(
		"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_TYPE, "+
			"CHARACTER_MAXIMUM_LENGTH, EXTRA, CHARACTER_SET_NAME, COLLATION_NAME, COLUMN_COMMENT "+
			"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ?",
		"TABLE_NAME", tables,
	)
	rows, err := s.conn.QueryContext(context.Background(), query, args...)
	if err != nil {
		return err
	}
	defer rows.Close()
	quoted := mariaDB(snap.Version)
	for rows.Next() {
		var tableName, columnName, dataType, nullable, columnType, extra string
		var length sql.NullInt64
		var columnDefault, charset, collation, comment sql.NullString
		if err = rows.Scan(
			&tableName, &columnName, &dataType, &nullable, &columnDefault, &columnType, &length, &extra,
			&charset, &collation, &comment,
		); err != nil {
			return err
		}
		table := snap.Tables[tableName]
		if table == nil {
			table = &Table{Columns: map[string]Column{}}
			snap.Tables[tableName] = table
		}
		column := liveColumn(
			columnName, dataType, nullable, columnType, extra, length, columnDefault, charset, collation, comment,
		)
		if quoted && column.HasDefault {
			column.DefaultLiteral = unquoteLiteral(column.DefaultLiteral)
		}
		table.Columns[columnName] = column
	}

	return rows.Err()
}

// mariaDB reports whether a server version string belongs to MariaDB.
func mariaDB(version string) bool {
	return strings.Contains(strings.ToLower(version), "mariadb")
}

// unquoteLiteral strips the quotes MariaDB puts around string defaults in information_schema.
func unquoteLiteral(value string) string {
	if len(value) < 2 || value[0] != '\'' || value[len(value)-1] != '\'' {
		return value
	}

	return strings.ReplaceAll(value[1:len(value)-1], "''", "'")
}

// loadIndexes reads every index of the given tables, in column order.
func (s *mysqlStore) loadIndexes(snap *Snapshot, tables []string) error {
	query, args := schemaFilter(
		"SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART "+
			"FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = ?",
		"TABLE_NAME", tables,
	)
	query += " ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
	rows, err := s.conn.QueryContext(context.Background(), query, args...)
	if err != nil {
		return err
	}
	defer rows.Close()
	grouped := map[string]map[string]*Index{}
	for rows.Next() {
		var tableName, indexName, columnName string
		var nonUnique, seq int
		var sub sql.NullInt64
		if err = rows.Scan(&tableName, &indexName, &nonUnique, &seq, &columnName, &sub); err != nil {
			return err
		}
		appendIndex(snap, grouped, tableName, indexName, columnName, nonUnique, sub)
	}

	return rows.Err()
}

// appendIndex adds one index column to the index it belongs to, creating it if needed.
func appendIndex(
	snap *Snapshot, grouped map[string]map[string]*Index,
	tableName, indexName, columnName string, nonUnique int, sub sql.NullInt64,
) {
	table := snap.Tables[tableName]
	if table == nil {
		return
	}
	if grouped[tableName] == nil {
		grouped[tableName] = map[string]*Index{}
	}

	idx := grouped[tableName][indexName]
	if idx == nil {
		idx = &Index{Name: indexName, Unique: nonUnique == 0, Primary: indexName == "PRIMARY"}
		grouped[tableName][indexName] = idx
		table.Indexes = append(table.Indexes, *idx)
	}

	prefix := 0
	if sub.Valid {
		prefix = int(sub.Int64)
	}
	idx.Columns = append(idx.Columns, columnName)
	idx.Prefix = append(idx.Prefix, prefix)
	if idx.Primary {
		table.PK = append(table.PK, columnName)
	}

	replaceIndex(table, *idx)
}

// replaceIndex overwrites the stored copy of an index with its latest state.
func replaceIndex(table *Table, idx Index) {
	for i := range table.Indexes {
		if table.Indexes[i].Name == idx.Name {
			table.Indexes[i] = idx
			return
		}
	}
}

// loadRowCounts counts the rows of every managed table that exists.
func (s *mysqlStore) loadRowCounts(snap *Snapshot) error {
	for _, table := range modelTables() {
		if snap.Tables[table.Name] == nil {
			continue
		}

		var count int64
		err := s.conn.QueryRowContext(
			context.Background(), "SELECT COUNT(*) FROM `"+table.Name+"`",
		).Scan(&count)
		if err != nil {
			return err
		}
		snap.RowCounts[table.Name] = count
	}

	return nil
}

// markLedgers records whether both ledger tables have the expected shape. It fails only when the
// ledger models cannot be reflected.
func (s *mysqlStore) markLedgers(snap *Snapshot) error {
	schemaSpec, dataSpec, err := ledgerSpecs()
	if err != nil {
		return err
	}
	snap.LedgerSchemaOK = ledgerShape(snap.Tables[schemaLedgerTable], schemaSpec)
	snap.LedgerDataOK = ledgerShape(snap.Tables[dataLedgerTable], dataSpec)

	return nil
}

// ledgerShape reports whether a ledger table has the shape its ledger model declares.
// Column types are compared by family, and unique indexes by columns rather than by name.
func ledgerShape(table *Table, spec tableSpec) bool {
	if table == nil {
		return true
	}
	if !sameCols(table.PK, spec.Baseline) {
		return false
	}

	for _, column := range spec.Columns {
		live, ok := table.Columns[column.Name]
		if !ok || !familyOK(column.Family, live.DataType) {
			return false
		}
	}

	for _, index := range spec.Indexes {
		if !index.Unique {
			continue
		}
		present, conflict := matchIndex(table.Indexes, index)
		if !present || conflict {
			return false
		}
	}

	return true
}

// loadLedgers reads both ledger tables, skipping any that is missing or unhealthy.
func (s *mysqlStore) loadLedgers(snap *Snapshot) error {
	readSchema := snap.Tables[schemaLedgerTable] != nil && snap.LedgerSchemaOK
	readData := snap.Tables[dataLedgerTable] != nil && snap.LedgerDataOK
	if !readSchema && !readData {
		return nil
	}

	db, err := s.orm()
	if err != nil {
		return err
	}
	if readSchema {
		if err = readLedgerRows[schemaLedgerRow](db, snap.Schema); err != nil {
			return err
		}
	}
	if readData {
		return readLedgerRows[dataLedgerRow](db, snap.Data)
	}

	return nil
}

// schemaFilter narrows an information_schema query to a set of table names.
func schemaFilter(base, column string, tables []string) (string, []any) {
	args := []any{managedDatabase}
	if len(tables) == 0 {
		return base, args
	}

	marks := make([]string, 0, len(tables))
	for _, name := range tables {
		if name == "" {
			continue
		}
		marks = append(marks, "?")
		args = append(args, name)
	}
	if len(marks) == 0 {
		return base, []any{managedDatabase}
	}

	return base + " AND " + column + " IN (" + strings.Join(marks, ", ") + ")", args
}
