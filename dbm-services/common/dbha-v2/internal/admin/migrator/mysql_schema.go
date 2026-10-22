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
)

func (s *mysqlStore) loadTables(snap *Snapshot) error {
	if err := s.loadColumns(snap); err != nil {
		return err
	}
	if err := s.loadIndexes(snap); err != nil {
		return err
	}
	return s.loadReferences(snap)
}

func (s *mysqlStore) loadColumns(snap *Snapshot) error {
	rows, err := s.conn.QueryContext(context.Background(),
		"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_TYPE, "+
			"CHARACTER_MAXIMUM_LENGTH, EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ?",
		managedDatabase,
	)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var tableName, columnName, dataType, nullable, columnType, extra string
		var length sql.NullInt64
		var columnDefault sql.NullString
		if err = rows.Scan(
			&tableName, &columnName, &dataType, &nullable, &columnDefault, &columnType, &length, &extra,
		); err != nil {
			return err
		}
		table := snap.Tables[tableName]
		if table == nil {
			table = &Table{Columns: map[string]Column{}}
			snap.Tables[tableName] = table
		}
		table.Columns[columnName] = liveColumn(
			columnName, dataType, nullable, columnType, extra, length, columnDefault,
		)
	}
	return rows.Err()
}

func (s *mysqlStore) loadIndexes(snap *Snapshot) error {
	rows, err := s.conn.QueryContext(context.Background(),
		"SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART "+
			"FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = ? "+
			"ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX",
		managedDatabase,
	)
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
		if err = appendIndex(snap, grouped, tableName, indexName, columnName, nonUnique, sub); err != nil {
			return err
		}
	}
	return rows.Err()
}

func appendIndex(
	snap *Snapshot, grouped map[string]map[string]*Index,
	tableName, indexName, columnName string, nonUnique int, sub sql.NullInt64,
) error {
	table := snap.Tables[tableName]
	if table == nil {
		return nil
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
	return replaceIndex(table, *idx)
}

func replaceIndex(table *Table, idx Index) error {
	for i := range table.Indexes {
		if table.Indexes[i].Name == idx.Name {
			table.Indexes[i] = idx
			return nil
		}
	}
	return nil
}

func (s *mysqlStore) loadRowCounts(snap *Snapshot) error {
	for _, table := range managedTables() {
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

func (s *mysqlStore) markLedgers(snap *Snapshot) {
	snap.LedgerSchemaOK = ledgerShape(snap.Tables["schema_migrations"], schemaLedgerColumns())
	snap.LedgerDataOK = ledgerShape(snap.Tables["dbha_data_migrations"], dataLedgerColumns())
}

func ledgerShape(table *Table, columns []columnSpec) bool {
	if table == nil {
		return true
	}
	if !sameCols(table.PK, []string{"version"}) {
		return false
	}
	for _, column := range columns {
		live, ok := table.Columns[column.Name]
		if !ok || !familyOK(column.Family, live.DataType) {
			return false
		}
	}
	present, conflict := matchIndex(table.Indexes, indexSpec{Name: "uk_name", Unique: true, Columns: []string{"name"}})
	return present && !conflict
}

func schemaLedgerColumns() []columnSpec {
	return []columnSpec{
		col("version", "int", ""),
		col("name", "varchar", ""),
		col("applied_at", "datetime", ""),
	}
}

func dataLedgerColumns() []columnSpec {
	return []columnSpec{
		col("version", "int", ""),
		col("name", "varchar", ""),
		col("required_schema_version", "int", ""),
		col("applied_at", "datetime", ""),
	}
}

func (s *mysqlStore) loadLedgers(snap *Snapshot) error {
	if snap.Tables["schema_migrations"] != nil && snap.LedgerSchemaOK {
		if err := s.readLedger("schema_migrations", snap.Schema); err != nil {
			return err
		}
	}
	if snap.Tables["dbha_data_migrations"] != nil && snap.LedgerDataOK {
		return s.readLedger("dbha_data_migrations", snap.Data)
	}
	return nil
}

func (s *mysqlStore) readLedger(table string, dest map[int64]Ledger) error {
	rows, err := s.conn.QueryContext(context.Background(), "SELECT version, name FROM `"+table+"`")
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var row Ledger
		if err = rows.Scan(&row.Version, &row.Name); err != nil {
			return err
		}
		dest[row.Version] = row
	}
	return rows.Err()
}

func (s *mysqlStore) loadStrategies(snap *Snapshot) error {
	table := snap.Tables["t_db_switching_strategy"]
	if table == nil || !strategyReady(snap) {
		return nil
	}
	rows, err := s.conn.QueryContext(context.Background(),
		"SELECT bk_biz_id, trigger_event_name, priority, IFNULL(updated_at, '') FROM `t_db_switching_strategy`",
	)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var row StrategyState
		if err = rows.Scan(&row.BkBizID, &row.Event, &row.Priority, &row.UpdatedAt); err != nil {
			return err
		}
		snap.Strategies = append(snap.Strategies, row)
	}
	return rows.Err()
}
