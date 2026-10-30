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
	"strconv"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	dataVersion = 1
	dataName    = "000001_default_global_strategies"
)

// Actions logged for one default strategy.
const (
	actionInitialize  = "initialize"
	actionRepair      = "repair"
	actionSkip        = "skip"
	actionKeepDeleted = "keep-deleted"
)

// defaultStrategies returns the global default strategies the migrator owns.
func defaultStrategies() []hamodel.DbSwitchingStrategy {
	return []hamodel.DbSwitchingStrategy{
		strategy(haprobe.DbEventNameDoubleCheckSshFailureV1, haprobe.DbEventNameReasonConnectionException),
		strategy(haprobe.DbEventNameSshAuthFailure, haprobe.DbEventNameReasonSSHAuthException),
		strategy(haprobe.DbEventNameSshTimeout, haprobe.DbEventNameReasonSshTimeout),
		strategy(haprobe.DbEventNameDiskWriteFailure, haprobe.DbEventNameReasonDiskWriteException),
		strategy(haprobe.DbEventNameUptimeFailure, haprobe.DbEventNameReasonUptimeException),
	}
}

// strategy builds one enabled host-scope switch strategy for an event and reason.
func strategy(event haprobe.DbEventName, reason haprobe.DbEventNameReason) hamodel.DbSwitchingStrategy {
	return hamodel.DbSwitchingStrategy{
		Name:                   event.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       event,
		TriggerEventNameReason: reason,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
	}
}

// strategySchemaVersion returns the schema version the strategy table was created at.
func strategySchemaVersion() int64 {
	for _, step := range schemaSteps() {
		if step.Table == hamodel.DbSwitchingStrategyTableName && step.Kind == objectTable {
			return step.Version
		}
	}

	return 0
}

// strategyHit is what the database says about one default strategy.
type strategyHit struct {
	Found   bool
	Status  string
	Deleted bool
}

// strategyRow is one live row that shares the identity of a default strategy.
// ReasonValid is false when trigger_event_name_reason is NULL. Deleted is true when deleted_at is not NULL.
type strategyRow struct {
	Reason      int
	ReasonValid bool
	Status      string
	Deleted     bool
}

// strategyAction is one logged decision for one default strategy.
type strategyAction struct {
	Seed   hamodel.DbSwitchingStrategy
	Action string
}

// strategyPlan is what the data step will do and how it will be reported.
type strategyPlan struct {
	Insert     []hamodel.DbSwitchingStrategy
	Actions    []strategyAction
	Complete   bool
	Initialize bool
	Unchanged  int
	SkipWrite  bool
}

// dataApplyResult is what callers may log. Skip and keep-deleted are known after
// planning. Initialize and repair are present only after the write commits.
type dataApplyResult struct {
	Actions   []strategyAction
	Unchanged int
}

// strategyReady reports whether the strategy table can be read and written.
func strategyReady(snap *Snapshot) bool {
	table := snap.Tables[hamodel.DbSwitchingStrategyTableName]
	if table == nil {
		return false
	}

	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if !ok || !strategyColumnsReady(table, spec) {
		return false
	}

	for _, index := range spec.Indexes {
		if !index.Unique {
			continue
		}
		present, conflict := matchIndex(table.Indexes, index)
		if !present || conflict {
			return false
		}
	}

	return true
}

// strategyColumnsReady reports whether every model column the data step reads or writes is usable.
// Auto-increment columns are skipped: inserts leave them to the database, and older tables may lack them.
func strategyColumnsReady(table *Table, spec tableSpec) bool {
	for _, column := range spec.Columns {
		if column.Target.AutoIncrement {
			continue
		}
		live, ok := table.Columns[column.Name]
		if !ok || !familyOK(column.Family, live.DataType) {
			return false
		}
	}

	return true
}

// ledgerView is the data ledger row for the current data version.
type ledgerView struct {
	Present bool
	Name    string
}

// ledgerFrom reads the data ledger row of the current data version.
func ledgerFrom(snap *Snapshot) ledgerView {
	if snap == nil {
		return ledgerView{}
	}
	row, ok := snap.Data[dataVersion]
	if !ok {
		return ledgerView{}
	}

	return ledgerView{Present: true, Name: row.Name}
}

// planDefaultStrategies decides what to do with every default strategy.
func planDefaultStrategies(
	empty bool, hits map[string]strategyHit, repair bool, ledger ledgerView,
) (strategyPlan, error) {
	if empty {
		return planEmptyStrategies(repair, ledger)
	}

	plan := strategyPlan{Complete: true}
	for _, seed := range defaultStrategies() {
		planKnownStrategy(&plan, seed, hits[seedIdentity(seed)], repair)
	}

	return plan, nil
}

// planEmptyStrategies plans for a strategy table that has no rows at all.
func planEmptyStrategies(repair bool, ledger ledgerView) (strategyPlan, error) {
	if ledger.Present && ledger.Name != dataName {
		return strategyPlan{}, fmt.Errorf("data ledger name conflict, version: %d", dataVersion)
	}

	// Data was applied once and the rows are gone: only repair may rewrite them.
	if ledger.Present && !repair {
		plan := strategyPlan{Complete: true, SkipWrite: true}
		for _, seed := range defaultStrategies() {
			plan.Actions = append(plan.Actions, strategyAction{Seed: seed, Action: actionSkip})
		}
		return plan, nil
	}

	plan := strategyPlan{Complete: true, Initialize: !ledger.Present}
	plan.Insert = append(plan.Insert, defaultStrategies()...)

	return plan, nil
}

// planKnownStrategy folds one already-present strategy into the plan.
func planKnownStrategy(plan *strategyPlan, seed hamodel.DbSwitchingStrategy, hit strategyHit, repair bool) {
	if !hit.Found {
		if repair {
			plan.Insert = append(plan.Insert, seed)
			return
		}
		plan.Complete = false
		plan.Actions = append(plan.Actions, strategyAction{Seed: seed, Action: actionSkip})
		return
	}

	// Soft-deleted rows stay deleted: the operator removed them on purpose.
	if strategyDeleted(hit) {
		plan.Actions = append(plan.Actions, strategyAction{Seed: seed, Action: actionKeepDeleted})
		return
	}

	plan.Unchanged++
}

// dataResult renders a plan for logging, once the write is known to be committed.
func dataResult(plan strategyPlan, committed bool) dataApplyResult {
	result := dataApplyResult{
		Actions:   append([]strategyAction{}, plan.Actions...),
		Unchanged: plan.Unchanged,
	}
	if !committed {
		return result
	}

	action := actionRepair
	if plan.Initialize {
		action = actionInitialize
	}
	for _, seed := range plan.Insert {
		result.Actions = append(result.Actions, strategyAction{Seed: seed, Action: action})
	}

	return result
}

// strategyDeleted reports whether a strategy row was soft-deleted.
func strategyDeleted(hit strategyHit) bool {
	return hit.Status == hamodel.StatusTypeDeleted.String() || hit.Deleted
}

// bestStrategyHit picks the highest-ranked row of one identity; no rows means not found.
// Rows of equal rank share the same deleted state, so whichever is picked yields the same action.
func bestStrategyHit(rows []strategyRow, reason int) strategyHit {
	best, bestRank := strategyHit{}, -1
	for _, row := range rows {
		if rank := strategyHitRank(row, reason); rank > bestRank {
			best, bestRank = rowHit(row), rank
		}
	}

	return best
}

// strategyHitRank orders rows that share one identity, the same way MySQL orders
// "(reason = ?) DESC, live DESC": the seed's own reason first, then another reason, then a NULL
// reason (NULL sorts last in descending order); within each group live rows come first.
func strategyHitRank(row strategyRow, reason int) int {
	level := 0
	if row.ReasonValid {
		level = 1
		if row.Reason == reason {
			level = 2
		}
	}

	rank := level * 2
	if !strategyDeleted(rowHit(row)) {
		rank++
	}

	return rank
}

// rowHit turns one live row into the hit the plan works with.
func rowHit(row strategyRow) strategyHit {
	return strategyHit{Found: true, Status: row.Status, Deleted: row.Deleted}
}

// seedIdentity is the business key of one default strategy.
func seedIdentity(seed hamodel.DbSwitchingStrategy) string {
	return strategyIdentity(seed.BkBizID, seed.TriggerEventName.String())
}

// strategyIdentity is the business key of one strategy: business plus event.
func strategyIdentity(bkBizID int, event string) string {
	return strconv.Itoa(bkBizID) + "\x00" + event
}
