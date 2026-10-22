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

func (s *mysqlStore) Load() (*Snapshot, error) {
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
	if err = s.loadTables(snap); err != nil {
		return nil, err
	}
	s.markLedgers(snap)
	if err = s.loadLedgers(snap); err != nil {
		return nil, err
	}
	return snap, nil
}

func (s *mysqlStore) LoadInventory() (*Snapshot, error) {
	snap, err := s.Load()
	if err != nil || !snap.Database {
		return snap, err
	}
	if err = s.loadRowCounts(snap); err != nil {
		return nil, err
	}
	if err = s.loadStrategies(snap); err != nil {
		return nil, err
	}
	return snap, nil
}

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
	grants, err := s.grants()
	if err != nil {
		return err
	}
	snap.CanWrite, snap.CanCreate = grantAccess(grants, managedDatabase)
	return nil
}

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

func (s *mysqlStore) boolVar(expr string) (bool, error) {
	var value int
	err := s.conn.QueryRowContext(context.Background(), "SELECT "+expr).Scan(&value)
	return value != 0, err
}

func unknownVariable(err error) bool {
	var mysqlErr *mysql.MySQLError
	return errors.As(err, &mysqlErr) && mysqlErr.Number == unknownSystemVariableCode
}

func (s *mysqlStore) grants() ([]string, error) {
	rows, err := s.conn.QueryContext(context.Background(), "SHOW GRANTS")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var line string
		if err = rows.Scan(&line); err != nil {
			return nil, err
		}
		out = append(out, line)
	}
	return out, rows.Err()
}

func grantAccess(lines []string, database string) (bool, bool) {
	global := grantSet{}
	target := grantSet{}
	for _, line := range lines {
		privs, kind, name, ok := parseGrant(line)
		if !ok {
			continue
		}
		switch kind {
		case grantGlobal:
			global.add(privs)
		case grantDatabase:
			if strings.EqualFold(name, database) {
				target.add(privs)
			}
		}
	}
	return global.canWrite(target), global.canCreate()
}

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

func (s *mysqlStore) useDB() error {
	_, err := s.conn.ExecContext(context.Background(), "USE `"+managedDatabase+"`")
	return err
}
