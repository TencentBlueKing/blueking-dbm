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

func liveColumn(
	name, dataType, nullable, columnType, extra string, length sql.NullInt64, columnDefault sql.NullString,
) Column {
	column := Column{
		Name: name, DataType: strings.ToLower(dataType), Nullable: nullable == "YES",
		Unsigned:      strings.Contains(strings.ToLower(columnType), "unsigned"),
		AutoIncrement: strings.Contains(strings.ToLower(extra), "auto_increment"),
	}
	if column.DataType == "varchar" || column.DataType == "char" {
		if length.Valid {
			column.CharLen = int(length.Int64)
		}
	}
	if columnDefault.Valid {
		column.HasDefault = true
		column.DefaultLiteral = columnDefault.String
	}
	return column
}

func (s *mysqlStore) loadReferences(snap *Snapshot) error {
	rows, err := s.conn.QueryContext(context.Background(),
		"SELECT DISTINCT REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE "+
			"WHERE REFERENCED_TABLE_SCHEMA = ? AND REFERENCED_TABLE_NAME IS NOT NULL",
		managedDatabase,
	)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var name string
		if err = rows.Scan(&name); err != nil {
			return err
		}
		if table := snap.Tables[name]; table != nil {
			table.Referenced = true
		}
	}
	return rows.Err()
}

func (s *mysqlStore) ProbeFacts(snap *Snapshot) error {
	if snap == nil || !snap.Database {
		return nil
	}
	for _, spec := range managedTables() {
		table := snap.Tables[spec.Name]
		if table == nil {
			continue
		}
		for _, column := range spec.Columns {
			live, ok := table.Columns[column.Name]
			if !ok || !needsFacts(column) {
				continue
			}
			if err := s.probeColumn(spec.Name, &live); err != nil {
				return err
			}
			table.Columns[column.Name] = live
		}
	}
	return nil
}

func needsFacts(column columnSpec) bool {
	return !column.Target.Nullable || column.Target.Unsigned || column.EmptyAsDefault || column.Target.AutoIncrement
}

func (s *mysqlStore) probeColumn(table string, column *Column) error {
	var err error
	column.HasNull, err = s.exists(table, column.Name, "IS NULL")
	if err != nil {
		return err
	}
	column.HasNegative, err = s.exists(table, column.Name, "< 0")
	if err != nil {
		return err
	}
	column.HasEmpty, err = s.exists(table, column.Name, "= ''")
	if err != nil {
		return err
	}
	column.HasNonNull, err = s.exists(table, column.Name, "IS NOT NULL")
	return err
}

func (s *mysqlStore) exists(table, column, predicate string) (bool, error) {
	query := fmt.Sprintf("SELECT 1 FROM `%s` WHERE `%s` %s LIMIT 1", table, column, predicate)
	var one int
	err := s.conn.QueryRowContext(context.Background(), query).Scan(&one)
	if err == sql.ErrNoRows {
		return false, nil
	}
	return err == nil, err
}

func (s *mysqlStore) ApplyConverge(plan convergePlan) error {
	for i, statement := range plan.Statements {
		if err := s.execConverge(statement, i == len(plan.Statements)-1 && isAlter(statement)); err != nil {
			return err
		}
	}
	return nil
}

func (s *mysqlStore) execConverge(statement string, lockWait bool) error {
	if !lockWait {
		_, err := s.conn.ExecContext(context.Background(), statement)
		return err
	}
	return s.withLockWait(func() error {
		_, err := s.conn.ExecContext(context.Background(), statement)
		return err
	})
}

func isAlter(statement string) bool {
	return strings.HasPrefix(statement, "ALTER ")
}

func (s *mysqlStore) withLockWait(fn func() error) error {
	var lockWait, innodbWait int
	err := s.conn.QueryRowContext(context.Background(),
		"SELECT @@session.lock_wait_timeout, @@session.innodb_lock_wait_timeout",
	).Scan(&lockWait, &innodbWait)
	if err != nil {
		return err
	}
	if _, err = s.conn.ExecContext(context.Background(), "SET SESSION lock_wait_timeout = 5"); err != nil {
		return err
	}
	if _, err = s.conn.ExecContext(context.Background(), "SET SESSION innodb_lock_wait_timeout = 5"); err != nil {
		return err
	}
	runErr := fn()
	_, _ = s.conn.ExecContext(context.Background(), "SET SESSION lock_wait_timeout = ?", lockWait)
	_, _ = s.conn.ExecContext(context.Background(), "SET SESSION innodb_lock_wait_timeout = ?", innodbWait)
	return runErr
}
