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
	"strings"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	classEmpty    = "empty"
	classComplete = "complete"
	classPartial  = "partial"
	classConflict = "conflict"
)

// Primary-key classes reported by keyClass.
const (
	keyTarget   = "target"
	keyLegacy   = "legacy"
	keyConflict = "conflict"
)

// classify reports how close an endpoint is to the managed schema.
// It returns the class, the missing tables, and the missing columns.
func classify(snap *Snapshot) (string, []string, []string) {
	if structuralConflict(snap) {
		return classConflict, nil, nil
	}

	var missing []string
	var columns []string
	present := 0
	for _, table := range modelTables() {
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
	case present == len(modelTables()):
		return classComplete, nil, columns
	default:
		return classPartial, missing, columns
	}
}

// structuralConflict reports whether any ledger row or schema object contradicts the model.
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

// legacyKey is a managed table whose primary key is a known historical shape.
type legacyKey struct {
	Table string
	PK    []string
}

// legacyKeys lists tables that still use a known legacy primary key.
func legacyKeys(snap *Snapshot) []legacyKey {
	if snap == nil {
		return nil
	}

	var out []legacyKey
	for _, spec := range modelTables() {
		live := snap.Tables[spec.Name]
		if live == nil || sameCols(live.PK, spec.Baseline) || !historicalPK(spec, live.PK) {
			continue
		}
		out = append(out, legacyKey{Table: spec.Name, PK: live.PK})
	}

	return out
}

// warnLegacyKeys logs every table that still uses a known legacy primary key.
func warnLegacyKeys(endpoint string, snap *Snapshot) {
	for _, key := range legacyKeys(snap) {
		logger.Warn(
			"known legacy primary key, endpoint: %s, table: %s, primary_key: %s",
			endpoint, key.Table, strings.Join(key.PK, ", "),
		)
	}
}

// keyClass labels a primary key as the target shape, a legacy shape, or a conflict.
func keyClass(spec tableSpec, pk []string) string {
	if sameCols(pk, spec.Baseline) {
		return keyTarget
	}
	if historicalPK(spec, pk) {
		return keyLegacy
	}

	return keyConflict
}

// versionText renders the server version, or "-" when it is unknown.
func versionText(snap *Snapshot) string {
	if snap == nil || snap.Version == "" {
		return "-"
	}

	return snap.Version
}
