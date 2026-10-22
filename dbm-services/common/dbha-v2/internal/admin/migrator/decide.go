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

// objectKind is the schema object a versioned step owns.
type objectKind int

const (
	objectTable objectKind = iota
	objectColumn
	objectIndex
	objectColumnDef
	objectPrimaryKey
)

// decision is what a schema step may do after inspecting the live database.
type decision int

const (
	decisionRecord decision = iota
	decisionApply
	decisionDrift
	decisionNeedAccept
	decisionConflict
)

// schemaChoice selects the next action for one schema step.
// recorded means the version ledger already contains the step.
// present means the live object exists and its type or key shape is acceptable.
// partialTables means some managed business tables exist and some do not.
func schemaChoice(
	recorded, present, typeConflict bool, kind objectKind, partialTables, rebuildTable bool, opts Options,
) decision {
	if convergeKind(kind) {
		return convergeChoice(present, typeConflict)
	}
	if typeConflict {
		return decisionConflict
	}
	if present {
		return decisionRecord
	}
	if recorded {
		if kind == objectTable && opts.RepairMissingTables {
			return decisionApply
		}
		if kind != objectTable && (opts.RepairMissing || rebuildTable) {
			return decisionApply
		}
		return decisionDrift
	}
	if kind == objectTable && partialTables && !opts.AcceptMissingTables && !opts.RepairMissingTables {
		return decisionNeedAccept
	}
	return decisionApply
}

func convergeKind(kind objectKind) bool {
	return kind == objectColumnDef || kind == objectPrimaryKey
}

func convergeChoice(present, typeConflict bool) decision {
	if typeConflict {
		return decisionConflict
	}
	if present {
		return decisionRecord
	}
	return decisionApply
}
