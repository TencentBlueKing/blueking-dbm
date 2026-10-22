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

type stepView struct {
	Present  bool
	Conflict bool
	Recorded bool
}

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
		if want.Name == step.Column && matchesHistorical(want, col) {
			return true, conflict
		}
		if want.Name == step.Column && !familyOK(want.Family, col.DataType) {
			return false, true
		}
	}
	return true, conflict
}

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
		return present, conflict || bad
	}
	return false, true
}

func knownPK(spec tableSpec, pk []string) bool {
	if sameCols(spec.Baseline, pk) {
		return true
	}
	return historicalPK(spec, pk)
}

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

func prefixAt(prefix []int, i int) int {
	if i >= len(prefix) {
		return 0
	}
	return prefix[i]
}

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

func integerType(actual string) bool {
	switch actual {
	case "tinyint", "smallint", "mediumint", "int", "integer", "bigint":
		return true
	default:
		return false
	}
}

func textType(actual string) bool {
	switch actual {
	case "tinytext", "text", "mediumtext", "longtext":
		return true
	default:
		return false
	}
}

func partialBusiness(snap *Snapshot) bool {
	present := 0
	for _, table := range managedTables() {
		if snap.Tables[table.Name] != nil {
			present++
		}
	}
	return present > 0 && present < len(managedTables())
}

func choiceName(choice decision) string {
	switch choice {
	case decisionRecord:
		return "record"
	case decisionApply:
		return "apply"
	case decisionDrift:
		return "drift"
	case decisionNeedAccept:
		return "accept"
	case decisionConflict:
		return "conflict"
	default:
		return "unknown"
	}
}

func schemaBlocker(snap *Snapshot, opts Options) error {
	partial := partialBusiness(snap)
	for _, step := range schemaSteps() {
		view := inspectStep(snap, step)
		rebuild := opts.RepairMissingTables && snap.Tables[step.Table] == nil
		choice := schemaChoice(
			view.Recorded, view.Present, view.Conflict, step.Kind, partial, rebuild, opts,
		)
		if choice == decisionRecord || choice == decisionApply {
			continue
		}
		return fmt.Errorf(
			"schema step blocked, version: %d, name: %s, result: %s",
			step.Version, step.Name, choiceName(choice),
		)
	}
	return nil
}
