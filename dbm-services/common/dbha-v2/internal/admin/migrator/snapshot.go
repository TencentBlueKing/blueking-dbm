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
	"maps"
	"strconv"
)

// Identity is the server identity used to order and deduplicate endpoints.
type Identity struct {
	ServerUUID string
	Hostname   string
	Port       int
	Endpoint   string
}

// Key is stable across processes so every migrator locks in the same order.
func (i Identity) Key() string {
	return i.ServerUUID + "|" + i.Hostname + "|" + strconv.Itoa(i.Port)
}

// Column is one live column.
type Column struct {
	Name           string
	DataType       string
	CharLen        int
	Unsigned       bool
	Nullable       bool
	AutoIncrement  bool
	HasDefault     bool
	DefaultLiteral string
	HasNull        bool
	NullCount      int
	HasNegative    bool
	HasEmpty       bool
	HasNonNull     bool
	MaxID          int64
}

// Index is one live index, including the primary key when Primary is set.
type Index struct {
	Name    string
	Unique  bool
	Primary bool
	Columns []string
	Prefix  []int
}

// Table is one live table.
type Table struct {
	Columns    map[string]Column
	Indexes    []Index
	PK         []string
	Referenced bool
}

// Ledger is one applied version row.
type Ledger struct {
	Version int64
	Name    string
}

// StrategyState is the identity and freshness of one strategy row.
type StrategyState struct {
	BkBizID   int
	Event     string
	Priority  int
	UpdatedAt string
	Status    string
	Deleted   bool
}

// Snapshot is a read-only view of one endpoint.
type Snapshot struct {
	Database       bool
	Tables         map[string]*Table
	Schema         map[int64]Ledger
	Data           map[int64]Ledger
	Strategies     []StrategyState
	ReadOnly       bool
	SuperReadOnly  bool
	CanWrite       bool
	CanCreate      bool
	Version        string
	VersionOK      bool
	LedgerSchemaOK bool
	LedgerDataOK   bool
	RowCounts      map[string]int64
}

func (s *Snapshot) clone() *Snapshot {
	if s == nil {
		return &Snapshot{}
	}
	out := *s
	out.Tables = map[string]*Table{}
	for name, table := range s.Tables {
		out.Tables[name] = table.clone()
	}
	out.Schema = maps.Clone(s.Schema)
	out.Data = maps.Clone(s.Data)
	out.Strategies = append([]StrategyState{}, s.Strategies...)
	out.RowCounts = maps.Clone(s.RowCounts)
	return &out
}

func (t *Table) clone() *Table {
	if t == nil {
		return nil
	}
	out := &Table{
		Columns: maps.Clone(t.Columns), PK: append([]string{}, t.PK...), Referenced: t.Referenced,
	}
	out.Indexes = make([]Index, len(t.Indexes))
	for index, item := range t.Indexes {
		out.Indexes[index] = item
		out.Indexes[index].Columns = append([]string{}, item.Columns...)
		out.Indexes[index].Prefix = append([]int{}, item.Prefix...)
	}
	return out
}
