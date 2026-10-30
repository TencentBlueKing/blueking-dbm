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
	decisionNeedRepair
	decisionConflict
)

// schemaChoice selects the next action for one schema step.
// recorded means the version ledger already contains the step.
// present means the live object exists and its type or key shape is acceptable.
// partialTables means some managed business tables exist and some do not.
func schemaChoice(
	recorded, present, typeConflict bool, kind objectKind, partialTables bool, opts Options,
) decision {
	// Column definitions and primary keys are converged to the model, not versioned.
	if convergeKind(kind) {
		return convergeChoice(present, typeConflict)
	}

	if typeConflict {
		return decisionConflict
	}

	// Already at the desired shape: only the ledger needs a row.
	if present {
		return decisionRecord
	}

	// Recorded but gone: rebuild when the operator asked for a repair, otherwise report drift.
	if recorded {
		if opts.RepairsSchema() {
			return decisionApply
		}
		return decisionDrift
	}

	// New table while some managed tables already exist: require schema repair as the opt-in.
	if kind == objectTable && partialTables && !opts.RepairsSchema() {
		return decisionNeedRepair
	}

	return decisionApply
}

// convergeKind reports whether the object is converged to the model instead of versioned.
func convergeKind(kind objectKind) bool {
	return kind == objectColumnDef || kind == objectPrimaryKey
}

// convergeChoice decides a converge-only object: conflict, already converged, or apply.
func convergeChoice(present, typeConflict bool) decision {
	if typeConflict {
		return decisionConflict
	}
	if present {
		return decisionRecord
	}
	return decisionApply
}
