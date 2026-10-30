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
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// liveColumn converts one information_schema row into a Column.
func liveColumn(
	name, dataType, nullable, columnType, extra string, length sql.NullInt64,
	columnDefault, charset, collation, comment sql.NullString,
) Column {
	column := Column{
		Name: name, DataType: strings.ToLower(dataType), Nullable: nullable == "YES",
		Unsigned:      strings.Contains(strings.ToLower(columnType), "unsigned"),
		AutoIncrement: strings.Contains(strings.ToLower(extra), "auto_increment"),
	}

	// Only character types carry a meaningful display length.
	if column.DataType == "varchar" || column.DataType == "char" {
		if length.Valid {
			column.CharLen = int(length.Int64)
		}
	}
	if charset.Valid {
		column.Charset = charset.String
	}
	if collation.Valid {
		column.Collation = collation.String
	}
	if comment.Valid {
		column.Comment = comment.String
	}
	if columnDefault.Valid && !(column.Nullable && strings.EqualFold(strings.TrimSpace(columnDefault.String), "NULL")) {
		column.HasDefault = true
		column.DefaultLiteral = columnDefault.String
	}

	column.OnUpdate = onUpdateLiteral(extra)

	return column
}

// onUpdateLiteral extracts the ON UPDATE CURRENT_TIMESTAMP token from EXTRA, if any.
func onUpdateLiteral(extra string) string {
	const marker = "on update "
	index := strings.Index(strings.ToLower(extra), marker)
	if index < 0 {
		return ""
	}

	rest := strings.TrimSpace(extra[index+len(marker):])
	if rest == "" {
		return ""
	}

	token := strings.TrimRight(strings.Fields(rest)[0], ",")
	if !currentTimestamp(token) {
		return ""
	}

	return token
}

// loadReferences marks managed tables that other tables reference.
func (s *mysqlStore) loadReferences(snap *Snapshot, tables []string) error {
	names := tables
	if len(tables) > 0 {
		names = []string{tables[0]}
	}
	query, args := schemaFilter(
		"SELECT DISTINCT REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE "+
			"WHERE REFERENCED_TABLE_SCHEMA = ? AND REFERENCED_TABLE_NAME IS NOT NULL",
		"REFERENCED_TABLE_NAME", names,
	)
	rows, err := s.conn.QueryContext(context.Background(), query, args...)
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

// ProbeFacts fills the data facts a step needs, limited to the step's scope.
func (s *mysqlStore) ProbeFacts(snap *Snapshot, scope factScope) error {
	if snap == nil || !snap.Database {
		return nil
	}

	for _, spec := range modelTables() {
		if scope.Table != "" && spec.Name != scope.Table {
			continue
		}
		table := snap.Tables[spec.Name]
		if table == nil {
			continue
		}

		for _, column := range spec.Columns {
			if scope.Column != "" && column.Name != scope.Column {
				continue
			}
			live, ok := table.Columns[column.Name]
			if !ok || !needsFacts(column) {
				continue
			}

			if err := s.probeColumn(spec.Name, &live, column); err != nil {
				return err
			}
			table.Columns[column.Name] = live
		}
	}

	return nil
}

// needsFacts reports whether a column has any predicate worth probing.
func needsFacts(column columnSpec) bool {
	return len(factPredicates(column)) > 0
}

// factPredicates lists the value predicates a column must be probed for.
func factPredicates(column columnSpec) []string {
	var predicates []string
	if !column.Target.Nullable || column.Target.AutoIncrement {
		predicates = append(predicates, "IS NULL")
	}
	if column.Target.Unsigned {
		predicates = append(predicates, "< 0")
	}
	if column.EmptyAsDefault {
		predicates = append(predicates, "= ''")
	}

	return predicates
}

// livePredicates drops the predicates the live column shape already rules out,
// so a NOT NULL or unsigned column skips a full-table scan that can never match.
func livePredicates(spec columnSpec, live Column) []string {
	var out []string
	for _, predicate := range factPredicates(spec) {
		if predicate == "IS NULL" && !live.Nullable {
			continue
		}
		if predicate == "< 0" && live.Unsigned {
			continue
		}
		out = append(out, predicate)
	}

	return out
}

// probeColumn runs every predicate of one column and stores what it found.
func (s *mysqlStore) probeColumn(table string, column *Column, spec columnSpec) error {
	for _, predicate := range livePredicates(spec, *column) {
		found, err := s.exists(table, column.Name, predicate)
		if err != nil {
			return err
		}

		switch predicate {
		case "IS NULL":
			column.HasNull = found
		case "< 0":
			column.HasNegative = found
		case "= ''":
			column.HasEmpty = found
		}
	}

	return nil
}

// exists reports whether at least one row matches the predicate.
func (s *mysqlStore) exists(table, column, predicate string) (bool, error) {
	quotedTable, err := quotedIdent(table)
	if err != nil {
		return false, err
	}
	quotedColumn, err := quotedIdent(column)
	if err != nil {
		return false, err
	}
	query := "SELECT 1 FROM " + quotedTable + " WHERE " + quotedColumn + " " + predicate + " LIMIT 1"

	var one int
	err = s.conn.QueryRowContext(context.Background(), query).Scan(&one)
	if err == sql.ErrNoRows {
		return false, nil
	}

	return err == nil, err
}

// ApplyConverge runs every statement of a converge plan and logs the outcome.
func (s *mysqlStore) ApplyConverge(plan convergePlan) error {
	started := time.Now()
	for _, statement := range plan.Statements {
		if err := s.execConverge(plan.Table, statement); err != nil {
			logStatement(s.endpoint, "converge", started, err)
			return err
		}
	}

	logStatement(s.endpoint, "converge", started, nil)

	return nil
}

// execConverge runs ALTER and backfill UPDATE statements under a lock-wait guard.
func (s *mysqlStore) execConverge(table, statement string) error {
	switch {
	case isAlter(statement):
		return s.withLockWait(func() error {
			_, err := s.conn.ExecContext(context.Background(), statement)
			return err
		})
	case isUpdate(statement):
		return s.withLockWait(func() error {
			return s.execBatched(table, statement)
		})
	default:
		_, err := s.conn.ExecContext(context.Background(), statement)
		return err
	}
}

// execBatched repeats a LIMIT-ed backfill UPDATE until a batch comes up short.
// Every batch commits on its own, so a failure keeps the rows already filled; a rerun continues
// from the rows that still match.
func (s *mysqlStore) execBatched(table, statement string) error {
	var filled int64
	for {
		affected, err := s.execAffected(statement)
		filled += affected
		if err != nil {
			logger.Warn(
				"converge backfill stopped, rerun continues from the remaining rows, "+
					"endpoint: %s, table: %s, filled_rows: %d, errmsg: %s",
				s.endpoint, table, filled, err,
			)
			return err
		}
		if affected < convergeBatchRows {
			return nil
		}
	}
}

// execAffected runs one statement and returns how many rows it changed.
func (s *mysqlStore) execAffected(statement string) (int64, error) {
	result, err := s.conn.ExecContext(context.Background(), statement)
	if err != nil {
		return 0, err
	}

	return result.RowsAffected()
}

// isAlter reports whether a statement is an ALTER TABLE.
func isAlter(statement string) bool {
	return strings.HasPrefix(statement, "ALTER ")
}

// isUpdate reports whether a statement is a backfill UPDATE.
func isUpdate(statement string) bool {
	return strings.HasPrefix(statement, "UPDATE ")
}

// withLockWait runs fn with a short lock wait, then restores the session settings.
func (s *mysqlStore) withLockWait(fn func() error) error {
	var lockWait, innodbWait int
	err := s.conn.QueryRowContext(context.Background(),
		"SELECT @@session.lock_wait_timeout, @@session.innodb_lock_wait_timeout",
	).Scan(&lockWait, &innodbWait)
	if err != nil {
		return err
	}

	exec := func(query string) error {
		_, err := s.conn.ExecContext(context.Background(), query)
		return err
	}

	return lockWaitScope(s.endpoint, exec, lockWaitValues{lockWait: lockWait, innodbWait: innodbWait}, fn)
}

// sessionExec runs one session statement on the migration connection.
type sessionExec func(query string) error

// lockWaitValues holds the session lock wait settings to restore.
type lockWaitValues struct {
	lockWait   int
	innodbWait int
}

// lockWaitScope sets a 5 second lock wait, runs fn, then restores every setting it changed.
// Restores use integer literals: a placeholder would be prepared on the server and can fail
// with 1461 once max_prepared_stmt_count is reached.
// A failed restore fails a successful fn, so later statements never inherit the short wait.
func lockWaitScope(endpoint string, exec sessionExec, original lockWaitValues, fn func() error) error {
	settings := []struct{ name, restore string }{
		{"lock_wait_timeout", "SET SESSION lock_wait_timeout = " + strconv.Itoa(original.lockWait)},
		{"innodb_lock_wait_timeout", "SET SESSION innodb_lock_wait_timeout = " + strconv.Itoa(original.innodbWait)},
	}

	applied := 0
	var runErr error
	for _, setting := range settings {
		if runErr = exec("SET SESSION " + setting.name + " = 5"); runErr != nil {
			break
		}
		applied++
	}
	if runErr == nil {
		runErr = fn()
	}

	var restoreErr error
	for i := applied - 1; i >= 0; i-- {
		if err := exec(settings[i].restore); err != nil {
			restoreErr = errors.Join(restoreErr, err)
		}
	}
	if restoreErr == nil {
		return runErr
	}
	if runErr != nil {
		logger.Warn("restore session lock wait failed, endpoint: %s, errmsg: %s", endpoint, restoreErr)
		return runErr
	}

	return fmt.Errorf("restore session lock wait failed, errmsg: %w", restoreErr)
}
