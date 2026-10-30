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
	"strings"

	"github.com/go-sql-driver/mysql"
)

const unknownSystemVariableCode uint16 = 1193

// Load reads the full snapshot of one endpoint.
func (s *mysqlStore) Load() (*Snapshot, error) {
	return s.loadSnapshot(nil)
}

// LoadStep reads only one table plus the two ledger tables.
func (s *mysqlStore) LoadStep(table string) (*Snapshot, error) {
	return s.loadSnapshot([]string{table, schemaLedgerTable, dataLedgerTable})
}

// loadSnapshot reads server state, tables, and ledgers, optionally for a table subset.
func (s *mysqlStore) loadSnapshot(tables []string) (*Snapshot, error) {
	if err := s.connect(); err != nil {
		return nil, err
	}

	snap := &Snapshot{
		Tables: map[string]*Table{}, Schema: map[int64]Ledger{}, Data: map[int64]Ledger{},
		VersionOK: true, LedgerSchemaOK: true, LedgerDataOK: true,
		RowCounts: map[string]int64{},
	}
	if err := s.loadServer(snap); err != nil {
		return nil, err
	}

	exists, err := s.databaseExists()
	if err != nil {
		return nil, err
	}
	snap.Database = exists
	if !exists {
		return snap, nil
	}

	if err = s.useDB(); err != nil {
		return nil, err
	}
	if err = s.loadTables(snap, tables); err != nil {
		return nil, err
	}
	if err = s.markLedgers(snap); err != nil {
		return nil, err
	}
	if err = s.loadLedgers(snap); err != nil {
		return nil, err
	}

	return snap, nil
}

// LoadInventory reads everything Load does, plus row counts.
func (s *mysqlStore) LoadInventory() (*Snapshot, error) {
	snap, err := s.Load()
	if err != nil || !snap.Database {
		return snap, err
	}

	if err = s.loadRowCounts(snap); err != nil {
		return nil, err
	}

	return snap, nil
}

// loadServer reads the version and the read-only flags.
func (s *mysqlStore) loadServer(snap *Snapshot) error {
	var version string
	if err := s.conn.QueryRowContext(context.Background(), "SELECT VERSION()").Scan(&version); err != nil {
		return err
	}
	snap.Version = strings.TrimSpace(version)
	snap.VersionOK = snap.Version != ""

	ro, superRO, err := s.readOnlyFlags()
	if err != nil {
		return err
	}
	snap.ReadOnly = ro
	snap.SuperReadOnly = superRO

	return nil
}

// readOnlyFlags reads read_only and super_read_only, tolerating old servers.
func (s *mysqlStore) readOnlyFlags() (bool, bool, error) {
	ro, err := s.boolVar("@@read_only")
	if err != nil {
		return false, false, err
	}

	superRO, err := s.boolVar("@@super_read_only")
	if err != nil && unknownVariable(err) {
		return ro, false, nil
	}

	return ro, superRO, err
}

// boolVar reads one boolean system variable.
func (s *mysqlStore) boolVar(expr string) (bool, error) {
	var value int
	err := s.conn.QueryRowContext(context.Background(), "SELECT "+expr).Scan(&value)

	return value != 0, err
}

// unknownVariable reports whether an error means "unknown system variable".
func unknownVariable(err error) bool {
	var mysqlErr *mysql.MySQLError
	return errors.As(err, &mysqlErr) && mysqlErr.Number == unknownSystemVariableCode
}

// databaseExists reports whether the managed database already exists.
func (s *mysqlStore) databaseExists() (bool, error) {
	var name string
	err := s.conn.QueryRowContext(
		context.Background(),
		"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = ?",
		managedDatabase,
	).Scan(&name)
	if err == sql.ErrNoRows {
		return false, nil
	}

	return err == nil, err
}

// useDB switches the pinned connection to the managed database.
func (s *mysqlStore) useDB() error {
	_, err := s.conn.ExecContext(context.Background(), "USE `"+managedDatabase+"`")

	return err
}
