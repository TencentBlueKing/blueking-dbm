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
	"sort"
	"strings"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	classEmpty    = "empty"
	classComplete = "complete"
	classPartial  = "partial"
	classConflict = "conflict"
)

func classify(snap *Snapshot) (string, []string, []string) {
	if structuralConflict(snap) {
		return classConflict, nil, nil
	}
	var missing []string
	var columns []string
	present := 0
	for _, table := range managedTables() {
		live := snap.Tables[table.Name]
		if live == nil {
			missing = append(missing, table.Name)
			continue
		}
		present++
		for _, column := range table.Columns {
			if _, ok := live.Columns[column.Name]; !ok {
				columns = append(columns, table.Name+"."+column.Name)
			}
		}
	}
	switch {
	case present == 0:
		return classEmpty, missing, nil
	case present == len(managedTables()):
		return classComplete, nil, columns
	default:
		return classPartial, missing, columns
	}
}

func structuralConflict(snap *Snapshot) bool {
	if snap != nil && (!snap.LedgerSchemaOK || !snap.LedgerDataOK) {
		return true
	}
	for _, step := range schemaSteps() {
		if inspectStep(snap, step).Conflict {
			return true
		}
	}
	return false
}

func legacyKeyNotes(snap *Snapshot) []string {
	if snap == nil {
		return nil
	}
	var notes []string
	for _, spec := range managedTables() {
		live := snap.Tables[spec.Name]
		if live == nil || sameCols(live.PK, spec.Baseline) || !historicalPK(spec, live.PK) {
			continue
		}
		notes = append(notes, spec.Name+"="+strings.Join(live.PK, ","))
	}
	return notes
}

func warnLegacyKeys(endpoint string, snap *Snapshot) {
	for _, note := range legacyKeyNotes(snap) {
		logger.Warn("known legacy primary key, endpoint: %s, primary_key: %s", endpoint, note)
	}
}

func keyClass(spec tableSpec, pk []string) string {
	if sameCols(pk, spec.Baseline) {
		return "target"
	}
	if historicalPK(spec, pk) {
		return "legacy"
	}
	return "conflict"
}

func joinNames(names []string) string {
	if len(names) == 0 {
		return "-"
	}
	return strings.Join(names, ",")
}

type tableProfile struct {
	Name     string
	Rows     int64
	PK       string
	KeyClass string
	Columns  string
	Unique   string
}

func inventoryProfiles(snap *Snapshot) []tableProfile {
	out := make([]tableProfile, 0, len(managedTables()))
	for _, spec := range managedTables() {
		live := snap.Tables[spec.Name]
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

func versionText(snap *Snapshot) string {
	if snap == nil || snap.Version == "" {
		return "-"
	}
	return snap.Version
}

func profileLine(profile tableProfile) string {
	return fmt.Sprintf(
		"table: %s, rows: %d, primary_key: %s, key_class: %s, columns: %s, unique_indexes: %s",
		profile.Name, profile.Rows, profile.PK, profile.KeyClass, profile.Columns, profile.Unique,
	)
}
