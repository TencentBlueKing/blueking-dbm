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
)

const schemaLedgerSQL = "CREATE TABLE `schema_migrations` (" +
	"`version` bigint NOT NULL," +
	"`name` varchar(255) NOT NULL," +
	"`applied_at` datetime NOT NULL," +
	"PRIMARY KEY (`version`)," +
	"UNIQUE KEY `uk_schema_migration_name` (`name`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

const dataLedgerSQL = "CREATE TABLE `dbha_data_migrations` (" +
	"`version` bigint NOT NULL," +
	"`name` varchar(255) NOT NULL," +
	"`required_schema_version` bigint NOT NULL," +
	"`applied_at` datetime NOT NULL," +
	"PRIMARY KEY (`version`)," +
	"UNIQUE KEY `uk_data_migration_name` (`name`)" +
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

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

func (s *mysqlStore) EnsureSchemaLedger() error {
	return s.ensureLedger("schema_migrations", schemaLedgerSQL)
}

func (s *mysqlStore) EnsureDataLedger() error {
	return s.ensureLedger("dbha_data_migrations", dataLedgerSQL)
}

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

func (s *mysqlStore) ExecDDL(stmt string) error {
	_, err := s.conn.ExecContext(context.Background(), stmt)
	return err
}

func (s *mysqlStore) RecordSchema(version int64, name string) error {
	return insertSchemaLedger(s.conn, version, name)
}

func insertSchemaLedger(conn *sql.Conn, version int64, name string) error {
	var existing string
	err := conn.QueryRowContext(
		context.Background(), "SELECT name FROM `schema_migrations` WHERE version = ?", version,
	).Scan(&existing)
	if err == nil {
		if existing != name {
			return fmt.Errorf("ledger name conflict, version: %d", version)
		}
		return nil
	}
	if err != sql.ErrNoRows {
		return err
	}
	_, err = conn.ExecContext(context.Background(),
		"INSERT INTO `schema_migrations` (version, name, applied_at) VALUES (?, ?, NOW())",
		version, name,
	)
	return err
}
