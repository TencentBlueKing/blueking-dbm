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
)

// stepView is how a step looks against the live database and the ledger.
type stepView struct {
	Present  bool
	Conflict bool
	Recorded bool
}

// inspectStep reads the live state of the object one step owns.
func inspectStep(snap *Snapshot, step schemaStep) stepView {
	var view stepView
	if row, ok := snap.Schema[step.Version]; ok {
		view.Recorded = row.Name == step.Name
		view.Conflict = row.Name != step.Name
	}

	switch step.Kind {
	case objectTable:
		view.Present, view.Conflict = tableState(snap, step, view.Conflict)
	case objectColumn:
		view.Present, view.Conflict = columnState(snap, step, view.Conflict)
	case objectIndex:
		view.Present, view.Conflict = indexState(snap, step, view.Conflict)
	case objectColumnDef:
		present, bad := columnDefView(snap, step)
		view.Present, view.Conflict = present, view.Conflict || bad
	case objectPrimaryKey:
		present, bad := primaryKeyView(snap, step)
		view.Present, view.Conflict = present, view.Conflict || bad
	}

	return view
}

// tableState reports whether a managed table exists with an acceptable primary key.
func tableState(snap *Snapshot, step schemaStep, conflict bool) (bool, bool) {
	spec, ok := tableByName(step.Table)
	live := snap.Tables[step.Table]
	if !ok || live == nil {
		return false, conflict
	}
	if !knownPK(spec, live.PK) {
		return false, true
	}
	return true, conflict
}

// columnState reports whether a column exists and still fits its declared family.
func columnState(snap *Snapshot, step schemaStep, conflict bool) (bool, bool) {
	live := snap.Tables[step.Table]
	if live == nil {
		return false, conflict
	}
	col, ok := live.Columns[step.Column]
	if !ok {
		return false, conflict
	}

	spec, _ := tableByName(step.Table)
	for _, want := range spec.Columns {
		if want.Name != step.Column {
			continue
		}
		if matchesHistorical(want, col) {
			return true, conflict
		}
		if !familyOK(want.Family, col.DataType) {
			return false, true
		}
	}

	return true, conflict
}

// indexState reports whether an index exists with the required uniqueness and prefix.
func indexState(snap *Snapshot, step schemaStep, conflict bool) (bool, bool) {
	live := snap.Tables[step.Table]
	if live == nil {
		return false, conflict
	}

	spec, _ := tableByName(step.Table)
	for _, want := range spec.Indexes {
		if want.Name != step.Index {
			continue
		}
		present, bad := matchIndex(live.Indexes, want)
		// A same-name index of another shape would make ADD INDEX fail with a duplicate key name.
		if !present && !bad && hasIndexNamed(live.Indexes, want.Name) {
			return false, true
		}
		return present, conflict || bad
	}

	return false, true
}

// hasIndexNamed reports whether a secondary index already uses the name; MySQL compares index names case-insensitively.
func hasIndexNamed(have []Index, name string) bool {
	for _, idx := range have {
		if !idx.Primary && strings.EqualFold(idx.Name, name) {
			return true
		}
	}

	return false
}

// knownPK reports whether a primary key is the baseline or a known historical shape.
func knownPK(spec tableSpec, pk []string) bool {
	return sameCols(spec.Baseline, pk) || historicalPK(spec, pk)
}

// sameCols compares two column lists in order.
func sameCols(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

// matchIndex finds a live index that satisfies a wanted index.
// It returns whether one was found and whether the only candidate conflicts.
func matchIndex(have []Index, want indexSpec) (bool, bool) {
	for _, idx := range have {
		if idx.Primary || !columnsAlign(idx.Columns, want.Columns) {
			continue
		}
		if idx.Unique != want.Unique && sameCols(idx.Columns, want.Columns) {
			return false, true
		}
		if idx.Unique == want.Unique && prefixSatisfied(idx.Prefix, want.Prefix, len(want.Columns)) {
			return true, false
		}
	}

	return false, false
}

// columnsAlign reports whether a live index starts with the wanted columns.
func columnsAlign(have, want []string) bool {
	if len(have) < len(want) {
		return false
	}
	for i := range want {
		if have[i] != want[i] {
			return false
		}
	}
	return true
}

// prefixSatisfied reports whether live prefix lengths cover the wanted ones.
func prefixSatisfied(have, want []int, n int) bool {
	for i := 0; i < n; i++ {
		haveN := prefixAt(have, i)
		wantN := prefixAt(want, i)
		if wantN == 0 && haveN != 0 {
			return false
		}
		if wantN > 0 && haveN != 0 && haveN < wantN {
			return false
		}
	}

	return true
}

// prefixAt reads one prefix length, treating a missing entry as no prefix.
func prefixAt(prefix []int, i int) int {
	if i >= len(prefix) {
		return 0
	}

	return prefix[i]
}

// familyOK reports whether a live column type still belongs to the declared family.
func familyOK(family, actual string) bool {
	actual = strings.ToLower(actual)
	switch family {
	case "int":
		return integerType(actual)
	case "varchar":
		return actual == "varchar" || actual == "char" || textType(actual)
	case "json":
		return actual == "json" || textType(actual)
	case "datetime":
		return actual == "datetime" || actual == "timestamp"
	case "text":
		return textType(actual)
	default:
		return actual == family
	}
}

// integerType reports whether a live type is an integer type.
func integerType(actual string) bool {
	switch actual {
	case "tinyint", "smallint", "mediumint", "int", "integer", "bigint":
		return true
	default:
		return false
	}
}

// textType reports whether a live type is a text type.
func textType(actual string) bool {
	switch actual {
	case "tinytext", "text", "mediumtext", "longtext":
		return true
	default:
		return false
	}
}

// partialBusiness reports whether only some managed tables exist on this endpoint.
func partialBusiness(snap *Snapshot) bool {
	present := 0
	for _, table := range modelTables() {
		if snap.Tables[table.Name] != nil {
			present++
		}
	}

	return present > 0 && present < len(modelTables())
}

// choiceName renders a decision for logs and error messages.
func choiceName(choice decision) string {
	switch choice {
	case decisionRecord:
		return "record"
	case decisionApply:
		return "apply"
	case decisionDrift:
		return "drift"
	case decisionNeedRepair:
		return "need_repair"
	case decisionConflict:
		return "conflict"
	default:
		return "unknown"
	}
}

// schemaBlocker fails fast when any schema step cannot be applied to this endpoint.
func schemaBlocker(snap *Snapshot, opts Options) error {
	partial := partialBusiness(snap)

	for _, step := range schemaSteps() {
		view := inspectStep(snap, step)
		choice := schemaChoice(view.Recorded, view.Present, view.Conflict, step.Kind, partial, opts)

		// Data-level blockers win over the decision itself.
		if result := stepDataBlock(snap, step, choice); result != "" {
			return blockedStepError(step, result)
		}
		if choice == decisionRecord || choice == decisionApply {
			continue
		}

		return blockedStepError(step, choiceName(choice))
	}

	return nil
}

// blockedStepError renders the standard "schema step blocked" error.
func blockedStepError(step schemaStep, result string) error {
	return fmt.Errorf(
		"schema step blocked, version: %d, name: %s, result: %s",
		step.Version, step.Name, result,
	)
}

// stepDataBlock reports a data-level reason that blocks a step, or "" when none.
func stepDataBlock(snap *Snapshot, step schemaStep, choice decision) string {
	if choice != decisionRecord && choice != decisionApply && choice != decisionConflict {
		return ""
	}

	// A unique index cannot be created while duplicate keys exist.
	if step.Kind == objectIndex && snap != nil && snap.DuplicateKeys[step.Table+"\x00"+step.Index] {
		return "duplicate"
	}

	if blockedNotNull(snap, step) {
		return "not_null"
	}

	return ""
}

// blockedNotNull reports whether a NOT NULL converge is impossible because of null data.
func blockedNotNull(snap *Snapshot, step schemaStep) bool {
	if step.Kind != objectColumnDef || snap == nil {
		return false
	}

	spec, ok := tableByName(step.Table)
	if !ok {
		return false
	}
	want := columnByName(spec, step.Column)
	if want.Name == "" || want.Target.Nullable || want.Target.HasDefault || want.Target.AutoIncrement {
		return false
	}

	live := snap.Tables[step.Table]
	if live == nil {
		return false
	}
	column, ok := live.Columns[step.Column]
	if !ok {
		return snap.NonEmpty[step.Table]
	}

	return column.HasNull
}
