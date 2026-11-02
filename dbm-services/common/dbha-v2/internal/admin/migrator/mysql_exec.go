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
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	schemaLedgerTable = "schema_migrations"
	dataLedgerTable   = "data_migrations"
)

// schemaLedgerSQL and dataLedgerSQL are frozen: they must create exactly the tables older
// migrators created. Their columns, primary key and unique index must match the ledger models.
const schemaLedgerSQL = "CREATE TABLE `" + schemaLedgerTable + "` (" +
	"`version` bigint NOT NULL," +
	"`name` varchar(255) NOT NULL," +
	"`applied_at` datetime NOT NULL," +
	"PRIMARY KEY (`version`)," +
	"UNIQUE KEY `uk_schema_migration_name` (`name`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

const dataLedgerSQL = "CREATE TABLE `" + dataLedgerTable + "` (" +
	"`version` bigint NOT NULL," +
	"`name` varchar(255) NOT NULL," +
	"`required_schema_version` bigint NOT NULL," +
	"`applied_at` datetime NOT NULL," +
	"PRIMARY KEY (`version`)," +
	"UNIQUE KEY `uk_data_migration_name` (`name`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

// EnsureDatabase creates the managed database if needed and switches to it.
func (s *mysqlStore) EnsureDatabase() error {
	exists, err := s.databaseExists()
	if err != nil {
		return err
	}

	if !exists {
		stmt := fmt.Sprintf(CreateDbIfNotExistSql, managedDatabase)
		if _, err = s.conn.ExecContext(context.Background(), stmt); err != nil {
			return err
		}
	}

	return s.useDB()
}

// EnsureSchemaLedger creates the schema ledger table if it is missing.
func (s *mysqlStore) EnsureSchemaLedger() error {
	return s.ensureLedger(schemaLedgerTable, schemaLedgerSQL)
}

// EnsureDataLedger creates the data ledger table if it is missing.
func (s *mysqlStore) EnsureDataLedger() error {
	return s.ensureLedger(dataLedgerTable, dataLedgerSQL)
}

// ensureLedger creates a ledger table only when it does not exist yet.
func (s *mysqlStore) ensureLedger(name, createSQL string) error {
	var count int
	err := s.conn.QueryRowContext(context.Background(),
		"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
		managedDatabase, name,
	).Scan(&count)
	if err != nil {
		return err
	}
	if count > 0 {
		return nil
	}

	_, err = s.conn.ExecContext(context.Background(), createSQL)

	return err
}

// ExecDDL runs one DDL statement and logs how it went.
func (s *mysqlStore) ExecDDL(stmt string) error {
	started := time.Now()
	err := s.execSchema(stmt)
	logStatement(s.endpoint, "ddl", started, err)

	return err
}

// execSchema runs ALTER statements under a lock-wait guard.
func (s *mysqlStore) execSchema(stmt string) error {
	if !isAlter(stmt) {
		_, err := s.conn.ExecContext(context.Background(), stmt)
		return err
	}

	return s.withLockWait(func() error {
		_, err := s.conn.ExecContext(context.Background(), stmt)
		return err
	})
}

// RecordSchema writes one schema ledger row, refusing to rename an existing version.
func (s *mysqlStore) RecordSchema(version int64, name string) error {
	db, err := s.orm()
	if err != nil {
		return err
	}
	now, err := serverNow(db)
	if err != nil {
		return err
	}

	return recordLedger(db, schemaLedgerRow{Version: version, Name: name, AppliedAt: now}, "ledger")
}

// logStatement logs the outcome and duration of one migration statement.
func logStatement(endpoint, kind string, started time.Time, err error) {
	elapsed := time.Since(started).Milliseconds()
	if err != nil {
		logger.Warn(
			"migrate statement failed, endpoint: %s, statement: %s, elapsed_ms: %d, errmsg: %s",
			endpoint, kind, elapsed, err,
		)
		return
	}
	logger.Info(
		"migrate statement finished, endpoint: %s, statement: %s, elapsed_ms: %d",
		endpoint, kind, elapsed,
	)
}
