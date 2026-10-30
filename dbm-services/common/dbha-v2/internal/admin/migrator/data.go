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
	"reflect"
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
// Deleted is true when deleted_at is not NULL.
type strategyRow struct {
	Status  string
	Deleted bool
}

// strategyConflict is an existing row that holds a unique key a default strategy would insert.
type strategyConflict struct {
	Index   string
	Name    string
	BkBizID int
	Event   string
	Reason  int
}

// strategyLookup is the value set one default strategy would occupy in one unique index.
type strategyLookup struct {
	Index  string
	Values map[string]any
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
func bestStrategyHit(rows []strategyRow) strategyHit {
	best, bestRank := strategyHit{}, -1
	for _, row := range rows {
		if rank := strategyHitRank(row); rank > bestRank {
			best, bestRank = rowHit(row), rank
		}
	}

	return best
}

// strategyHitRank orders rows that share one identity: live rows before soft-deleted ones.
func strategyHitRank(row strategyRow) int {
	if strategyDeleted(rowHit(row)) {
		return 0
	}

	return 1
}

// rowHit turns one live row into the hit the plan works with.
func rowHit(row strategyRow) strategyHit {
	return strategyHit{Found: true, Status: row.Status, Deleted: row.Deleted}
}

// seedIdentity is the business key of one default strategy.
func seedIdentity(seed hamodel.DbSwitchingStrategy) string {
	return strategyIdentity(seed.BkBizID, seed.TriggerEventName.String(), int(seed.TriggerEventNameReason))
}

// strategyIdentity is the business key of one strategy: business, event and reason,
// the same columns as the idx_biz_event_reason unique index.
func strategyIdentity(bkBizID int, event string, reason int) string {
	return strconv.Itoa(bkBizID) + "\x00" + event + "\x00" + strconv.Itoa(reason)
}

// insertConflictsWanted reports whether a plan writes rows that existing rows could collide with.
func insertConflictsWanted(empty bool, plan strategyPlan) bool {
	return !empty && plan.Complete && !plan.SkipWrite && len(plan.Insert) > 0
}

// strategyLookups lists the value set a default strategy occupies in every unique index of the model.
// Column values come from the model fields by their gorm column tag, so a new unique index is covered
// without listing its columns here.
func strategyLookups(seed hamodel.DbSwitchingStrategy) ([]strategyLookup, error) {
	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if !ok {
		return nil, fmt.Errorf("strategy table is not managed")
	}
	values, err := modelColumnValues(seed)
	if err != nil {
		return nil, err
	}

	return strategyLookupsFrom(spec, values)
}

// strategyLookupsFrom builds one lookup per unique index of spec from model column values.
// It fails when a unique index column has no model value.
func strategyLookupsFrom(spec tableSpec, values map[string]any) ([]strategyLookup, error) {
	var lookups []strategyLookup
	for _, index := range spec.Indexes {
		if !index.Unique {
			continue
		}
		lookup := strategyLookup{Index: index.Name, Values: map[string]any{}}
		for _, column := range index.Columns {
			value, ok := values[column]
			if !ok {
				return nil, fmt.Errorf("unique index column has no model value, index: %s, column: %s",
					index.Name, column)
			}
			lookup.Values[column] = value
		}
		lookups = append(lookups, lookup)
	}

	return lookups, nil
}

// modelColumnValues maps every gorm column of a model value to a driver-ready value.
func modelColumnValues(model any) (map[string]any, error) {
	value := reflect.ValueOf(model)
	if value.Kind() == reflect.Pointer {
		value = value.Elem()
	}

	values := map[string]any{}
	for i := 0; i < value.NumField(); i++ {
		field := value.Type().Field(i)
		if field.PkgPath != "" {
			continue
		}
		parsed, ok, err := parseField(field)
		if err != nil {
			return nil, err
		}
		if !ok {
			continue
		}
		if plain, ok := plainValue(value.Field(i)); ok {
			values[parsed.column] = plain
		}
	}

	return values, nil
}

// plainValue unwraps named string and integer types to their base value.
func plainValue(value reflect.Value) (any, bool) {
	switch value.Kind() {
	case reflect.String:
		return value.String(), true
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return value.Int(), true
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return value.Uint(), true
	default:
		return nil, false
	}
}

// uniqueConflictError renders the blocker for a default strategy that an existing row would collide with.
func uniqueConflictError(seed hamodel.DbSwitchingStrategy, conflict strategyConflict) error {
	return fmt.Errorf(
		"data blocked, bk_biz_id: %d, trigger_event_name: %s, trigger_event_name_reason: %d, index: %s, "+
			"conflict_name: %s, conflict_bk_biz_id: %d, conflict_event: %s, conflict_reason: %d, "+
			"result: unique_conflict",
		seed.BkBizID, seed.TriggerEventName, int(seed.TriggerEventNameReason), conflict.Index,
		conflict.Name, conflict.BkBizID, conflict.Event, conflict.Reason,
	)
}

// strategyPlanReady reports whether the strategy table has every column the data plan reads,
// so the plan can be checked before schema convergence runs.
func strategyPlanReady(snap *Snapshot) bool {
	if snap == nil || !snap.Database {
		return false
	}
	table := snap.Tables[hamodel.DbSwitchingStrategyTableName]
	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if table == nil || !ok {
		return false
	}

	columns := []string{
		hamodel.DbSwitchingStrategyFieldBkBizID,
		hamodel.DbSwitchingStrategyFieldTriggerEventName,
		hamodel.DbSwitchingStrategyFieldTriggerEventNameReason,
		hamodel.DbSwitchingStrategyFieldStatus,
		hamodel.DbSwitchingStrategyFieldDeletedAt,
		hamodel.DbSwitchingStrategyFieldName,
	}
	for _, index := range spec.Indexes {
		if index.Unique {
			columns = append(columns, index.Columns...)
		}
	}

	return columnsPresent(table, columns)
}
