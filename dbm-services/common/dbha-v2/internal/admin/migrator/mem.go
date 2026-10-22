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
	"fmt"
	"sync"
)

var (
	memLockMu sync.Mutex
	memLocks  = map[string]*sync.Mutex{}
)

// memStore is an in-memory target used by unit tests.
type memStore struct {
	endpoint       string
	ident          Identity
	snap           *Snapshot
	ddl            int
	applied        []string
	pkAlters       int
	failDDL        bool
	failAfterFill  bool
	failRecord     bool
	txFail         bool
	held           *sync.Mutex
	baseLoads      int
	inventoryLoads int
}

func newMem(endpoint string, id Identity) *memStore {
	return &memStore{
		endpoint: endpoint,
		ident:    id,
		snap: &Snapshot{
			Tables:         map[string]*Table{},
			Schema:         map[int64]Ledger{},
			Data:           map[int64]Ledger{},
			CanWrite:       true,
			CanCreate:      true,
			VersionOK:      true,
			LedgerSchemaOK: true,
			LedgerDataOK:   true,
			RowCounts:      map[string]int64{},
		},
	}
}

func (m *memStore) Endpoint() string { return m.endpoint }

func (m *memStore) Identity() (Identity, error) { return m.ident, nil }

func (m *memStore) Lock() error {
	mu := sharedMemLock(m.ident.Key() + "|" + lockName())
	mu.Lock()
	m.held = mu
	return nil
}

func (m *memStore) Unlock() error {
	if m.held == nil {
		return nil
	}
	m.held.Unlock()
	m.held = nil
	return nil
}

func sharedMemLock(name string) *sync.Mutex {
	memLockMu.Lock()
	defer memLockMu.Unlock()
	mu, ok := memLocks[name]
	if !ok {
		mu = &sync.Mutex{}
		memLocks[name] = mu
	}
	return mu
}

func (m *memStore) Load() (*Snapshot, error) {
	m.baseLoads++
	snap := m.snap.clone()
	snap.RowCounts = map[string]int64{}
	snap.Strategies = nil
	return snap, nil
}

func (m *memStore) LoadInventory() (*Snapshot, error) {
	m.inventoryLoads++
	return m.snap.clone(), nil
}

func (m *memStore) EnsureDatabase() error {
	m.snap.Database = true
	return nil
}

func (m *memStore) EnsureSchemaLedger() error {
	if !m.snap.LedgerSchemaOK {
		return fmt.Errorf("migration ledger conflict")
	}
	m.snap.Tables["schema_migrations"] = ledgerTable([]string{"version", "name", "applied_at"})
	return nil
}

func (m *memStore) EnsureDataLedger() error {
	if !m.snap.LedgerDataOK {
		return fmt.Errorf("migration ledger conflict")
	}
	m.snap.Tables["dbha_data_migrations"] = ledgerTable(
		[]string{"version", "name", "required_schema_version", "applied_at"},
	)
	return nil
}

func ledgerTable(columns []string) *Table {
	table := &Table{Columns: map[string]Column{}, PK: []string{"version"}}
	for _, name := range columns {
		family := "int"
		if name == "name" {
			family = "varchar"
		}
		if name == "applied_at" {
			family = "datetime"
		}
		table.Columns[name] = Column{Name: name, DataType: family}
	}
	table.Indexes = []Index{{
		Name: "uk_name", Unique: true, Columns: []string{"name"},
	}}
	return table
}
