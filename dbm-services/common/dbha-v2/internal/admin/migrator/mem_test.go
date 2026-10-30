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
	"strings"
	"sync"
)

var (
	memLockMu sync.Mutex
	memLocks  = map[string]*sync.Mutex{}
)

// duplicateKey is the memStore key of one duplicate probe result.
func duplicateKey(table string, columns []string) string {
	return table + "\x00" + strings.Join(columns, "\x00")
}

// StrategyState is one strategy row held by memStore. ReasonNull models a NULL trigger_event_name_reason.
type StrategyState struct {
	Name       string
	BkBizID    int
	Event      string
	Reason     int
	ReasonNull bool
	Priority   int
	UpdatedAt  string
	Status     string
	Deleted    bool
}

// memServer holds the strategy rows of one server; stores of the same server share it.
type memServer struct {
	strategies []StrategyState
}

// memStore is an in-memory target used by unit tests.
type memStore struct {
	*memServer
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
	failLoad       bool
	probes         []factScope
	duplicates     map[string]bool
	nonEmpty       map[string]bool
}

// newMem builds an in-memory store that starts clean and writable.
func newMem(endpoint string, id Identity) *memStore {
	return &memStore{
		memServer: &memServer{},
		endpoint:  endpoint,
		ident:     id,
		snap: &Snapshot{
			Tables:         map[string]*Table{},
			Schema:         map[int64]Ledger{},
			Data:           map[int64]Ledger{},
			VersionOK:      true,
			LedgerSchemaOK: true,
			LedgerDataOK:   true,
			RowCounts:      map[string]int64{},
		},
	}
}

// Endpoint returns the endpoint this store stands for.
func (m *memStore) Endpoint() string { return m.endpoint }

// Identity returns the configured server identity.
func (m *memStore) Identity() (Identity, error) { return m.ident, nil }

// Lock takes the process-wide mutex that stands in for an advisory lock.
func (m *memStore) Lock() error {
	mu := sharedMemLock(m.ident.Key() + "|" + lockName())
	mu.Lock()
	m.held = mu

	return nil
}

// Unlock releases the mutex taken by Lock, if any.
func (m *memStore) Unlock() error {
	if m.held == nil {
		return nil
	}
	m.held.Unlock()
	m.held = nil

	return nil
}

// sharedMemLock returns the mutex for one lock name, creating it on first use.
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

// Load returns a snapshot with row counts cleared, as a fresh load would.
func (m *memStore) Load() (*Snapshot, error) {
	m.baseLoads++

	snap := m.snap.clone()
	snap.RowCounts = map[string]int64{}

	return snap, nil
}

// LoadStep behaves like Load because the in-memory store has no per-table cost.
func (m *memStore) LoadStep(string) (*Snapshot, error) {
	return m.Load()
}

// DuplicateSamples returns one sample when a duplicate key is configured for the key columns.
func (m *memStore) DuplicateSamples(table string, keys []keyExpr, _ int) ([]duplicateSample, error) {
	columns := make([]string, 0, len(keys))
	for _, key := range keys {
		columns = append(columns, key.Column)
	}
	if !m.duplicates[duplicateKey(table, columns)] {
		return nil, nil
	}

	return []duplicateSample{{Values: columns, Rows: 2}}, nil
}

// TableNonEmpty reports whether a configured table has rows.
func (m *memStore) TableNonEmpty(table string) (bool, error) {
	return m.nonEmpty[table], nil
}

// LoadInventory returns the full snapshot, or fails when the test asked for it.
func (m *memStore) LoadInventory() (*Snapshot, error) {
	if m.failLoad {
		return nil, fmt.Errorf("load failed")
	}
	m.inventoryLoads++

	return m.snap.clone(), nil
}

// EnsureDatabase marks the database as present.
func (m *memStore) EnsureDatabase() error {
	m.snap.Database = true

	return nil
}

// EnsureSchemaLedger creates the schema ledger table.
func (m *memStore) EnsureSchemaLedger() error {
	if !m.snap.LedgerSchemaOK {
		return fmt.Errorf("migration ledger conflict")
	}
	m.snap.Tables[schemaLedgerTable] = ledgerTable([]string{"version", "name", "applied_at"})

	return nil
}

// EnsureDataLedger creates the data ledger table.
func (m *memStore) EnsureDataLedger() error {
	if !m.snap.LedgerDataOK {
		return fmt.Errorf("migration ledger conflict")
	}
	m.snap.Tables[dataLedgerTable] = ledgerTable(
		[]string{"version", "name", "required_schema_version", "applied_at"},
	)

	return nil
}

// ledgerTable builds a minimal ledger table with the given columns.
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
