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
	"sort"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

const statusTable = hamodel.DbhaDataStatusTableName

// tableProfile is one managed table summarized for test assertions.
type tableProfile struct {
	Name     string
	Rows     int64
	PK       string
	KeyClass string
	Columns  string
	Unique   string
}

// statusSpec returns the spec of the status table, which the migrator always manages.
func statusSpec() tableSpec {
	spec, ok := tableByName(statusTable)
	if !ok {
		panic("status table is not managed")
	}

	return spec
}

// strategySpec returns the spec of the switching strategy table.
func strategySpec() tableSpec {
	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if !ok {
		panic("strategy table is not managed")
	}

	return spec
}

// legacyKeyNotes renders legacy primary keys as "table=col,col" notes.
func legacyKeyNotes(snap *Snapshot) []string {
	keys := legacyKeys(snap)

	notes := make([]string, 0, len(keys))
	for _, key := range keys {
		notes = append(notes, key.Table+"="+strings.Join(key.PK, ","))
	}

	return notes
}

// joinNames joins names, using "-" when there is nothing to show.
func joinNames(names []string) string {
	if len(names) == 0 {
		return "-"
	}

	return strings.Join(names, ",")
}

// inventoryProfiles builds one profile per managed table, present or not.
func inventoryProfiles(snap *Snapshot) []tableProfile {
	out := make([]tableProfile, 0, len(modelTables()))
	for _, spec := range modelTables() {
		live := liveTable(snap, spec.Name)
		profile := tableProfile{Name: spec.Name, PK: "-", Columns: "-", Unique: "-"}
		if snap != nil && snap.RowCounts != nil {
			profile.Rows = snap.RowCounts[spec.Name]
		}
		if live == nil {
			out = append(out, profile)
			continue
		}

		profile.PK = joinNames(live.PK)
		profile.KeyClass = keyClass(spec, live.PK)
		profile.Columns = columnProfile(live)
		profile.Unique = uniqueProfile(live)
		out = append(out, profile)
	}

	return out
}

// columnProfile renders the live columns as a sorted "name:type" list.
func columnProfile(table *Table) string {
	if table == nil || len(table.Columns) == 0 {
		return "-"
	}

	names := make([]string, 0, len(table.Columns))
	for name, column := range table.Columns {
		names = append(names, name+":"+column.DataType)
	}
	sort.Strings(names)

	return strings.Join(names, ",")
}

// uniqueProfile renders the live unique secondary indexes as a sorted list.
func uniqueProfile(table *Table) string {
	if table == nil {
		return "-"
	}

	var parts []string
	for _, index := range table.Indexes {
		if index.Primary || !index.Unique {
			continue
		}
		parts = append(parts, index.Name+"("+strings.Join(index.Columns, ",")+")")
	}
	sort.Strings(parts)

	return joinNames(parts)
}

func TestInventoryProfilesToleratesNilSnapshot(t *testing.T) {
	profiles := inventoryProfiles(nil)
	if len(profiles) != len(modelTables()) || profiles[0].PK != "-" {
		t.Fatal("nil snapshot did not render empty profiles")
	}
}
