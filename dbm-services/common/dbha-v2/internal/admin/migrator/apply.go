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

	"dbm-services/common/dbha-v2/pkg/logger"
)

// migrateResult counts what one endpoint did, for the final summary log.
type migrateResult struct {
	schemaUnchanged int
	schemaCreated   int
	schemaRepaired  int
	schemaConverged int
	dataUnchanged   int
	dataInitialized int
	dataRepaired    int
	dataSkipped     int
	dataKeptDeleted int
}

// applyOne migrates one endpoint and logs a per-endpoint summary.
func applyOne(store Store, opts Options) error {
	var result migrateResult

	if opts.RunsSchema() {
		if err := applySchema(store, opts, &result); err != nil {
			return err
		}
	}

	if opts.RunsData() {
		data, err := store.ApplyStrategies(opts.RepairsData())
		if err != nil {
			return fmt.Errorf("data step failed, endpoint: %s, errmsg: %w", store.Endpoint(), err)
		}
		logDataActions(store.Endpoint(), data.Actions)
		addDataResult(&result, data)
	}

	logMigrateFinished(store.Endpoint(), result)

	return nil
}

// applySchema prepares the database and replays every versioned schema step.
func applySchema(store Store, opts Options, result *migrateResult) error {
	snap, err := store.Load()
	if err != nil {
		return endpointError("load schema snapshot", store, err)
	}
	warnLegacyKeys(store.Endpoint(), snap)

	partial := partialBusiness(snap)

	if err = store.EnsureDatabase(); err != nil {
		return endpointError("ensure database", store, err)
	}
	if err = store.EnsureSchemaLedger(); err != nil {
		return endpointError("ensure schema ledger", store, err)
	}

	for _, step := range schemaSteps() {
		if err = applyStep(store, opts, step, partial, result); err != nil {
			return err
		}
	}

	return nil
}

// applyStep decides and executes one versioned schema step.
func applyStep(
	store Store, opts Options, step schemaStep, partial bool, result *migrateResult,
) error {
	snap, err := stepSnapshot(store, step)
	if err != nil {
		return stepError("load schema snapshot", store, step, err)
	}

	view := inspectStep(snap, step)
	choice := schemaChoice(view.Recorded, view.Present, view.Conflict, step.Kind, partial, opts)

	switch choice {
	case decisionRecord:
		if err = store.RecordSchema(step.Version, step.Name); err != nil {
			return stepError("record schema ledger", store, step, err)
		}
		result.schemaUnchanged++
		return nil
	case decisionApply:
		if err = recheckDuplicates(store, snap, step); err != nil {
			return err
		}
		changed, err := applyChosen(store, step, snap)
		if err != nil {
			return err
		}
		if err = verifyStep(store, step); err != nil {
			return err
		}
		if err = store.RecordSchema(step.Version, step.Name); err != nil {
			return stepError("record schema ledger", store, step, err)
		}
		if !changed {
			result.schemaUnchanged++
			return nil
		}
		noteSchemaChange(store.Endpoint(), step, view.Recorded, result)
		return nil
	default:
		return fmt.Errorf(
			"schema step blocked, endpoint: %s, version: %d, result: %s",
			store.Endpoint(), step.Version, choiceName(choice),
		)
	}
}

// recheckDuplicates probes again, right before the DDL, the duplicate rows that would make a unique
// index or a primary key rebuild fail. Earlier steps may have added or backfilled the key columns
// since the precheck ran. It calls the duplicate probe directly, never ProbeFacts.
func recheckDuplicates(store Store, snap *Snapshot, step schemaStep) error {
	if snap == nil || !snap.Database || (step.Kind != objectIndex && step.Kind != objectPrimaryKey) {
		return nil
	}
	spec, ok := tableByName(step.Table)
	live := snap.Tables[step.Table]
	if !ok || live == nil {
		return nil
	}

	return recheckStepDuplicates(store, snap, spec, live, step)
}

// recheckStepDuplicates probes one step's key on spec and blocks the step on duplicates.
func recheckStepDuplicates(store Store, snap *Snapshot, spec tableSpec, live *Table, step schemaStep) error {
	if snap.DuplicateKeys == nil {
		snap.DuplicateKeys = map[string]bool{}
	}

	var err error
	switch step.Kind {
	case objectIndex:
		if index, found := findIndexSpec(spec, step.Index); found {
			err = probeIndexDuplicates(store, snap, spec, live, index)
		}
	case objectPrimaryKey:
		err = probePrimaryKeyDuplicates(store, snap, spec, live)
	}
	if err != nil {
		return stepError("probe duplicate keys", store, step, err)
	}
	if duplicateBlocked(snap, step) {
		return fmt.Errorf(
			"schema step blocked, endpoint: %s, version: %d, result: duplicate",
			store.Endpoint(), step.Version,
		)
	}

	return nil
}

// verifyStep reloads the object and fails when the applied DDL did not take effect.
func verifyStep(store Store, step schemaStep) error {
	snap, err := stepSnapshot(store, step)
	if err != nil {
		return stepError("load schema snapshot", store, step, err)
	}
	view := inspectStep(snap, step)
	if view.Present && !view.Conflict {
		return nil
	}

	result := "missing"
	if view.Conflict {
		result = "conflict"
	}

	return fmt.Errorf(
		"verify schema DDL failed, endpoint: %s, version: %d, result: %s",
		store.Endpoint(), step.Version, result,
	)
}

// stepSnapshot loads what one step inspects. Only converge steps read value facts,
// so table, column, and index steps skip the probe queries.
func stepSnapshot(store Store, step schemaStep) (*Snapshot, error) {
	if !convergeKind(step.Kind) {
		return store.LoadStep(step.Table)
	}

	return probed(store, factScopeFor(step))
}

// probed loads the snapshot for a step and fills in the facts that step needs.
func probed(store Store, scope factScope) (*Snapshot, error) {
	var snap *Snapshot
	var err error
	if scope.Table == "" {
		snap, err = store.Load()
	} else {
		snap, err = store.LoadStep(scope.Table)
	}
	if err != nil || snap == nil || !snap.Database {
		return snap, err
	}

	if err = store.ProbeFacts(snap, scope); err != nil {
		return nil, err
	}

	return snap, nil
}

// factScopeFor narrows the probe to the single column a column step cares about.
func factScopeFor(step schemaStep) factScope {
	switch step.Kind {
	case objectColumn, objectColumnDef:
		return factScope{Table: step.Table, Column: step.Column}
	default:
		return factScope{Table: step.Table}
	}
}

// applyChosen runs the SQL of a step and reports whether anything changed.
// snap is the probed snapshot the decision was made on; nothing has written since.
func applyChosen(store Store, step schemaStep, snap *Snapshot) (bool, error) {
	if !convergeKind(step.Kind) {
		if err := store.ExecDDL(step.Apply); err != nil {
			return false, stepError("apply schema DDL", store, step, err)
		}
		return true, nil
	}

	changed, err := applyConvergeStep(store, step, snap)
	if err != nil {
		return false, stepError("apply schema DDL", store, step, err)
	}

	return changed, nil
}

// applyConvergeStep applies a converge plan built from the live table shape.
func applyConvergeStep(store Store, step schemaStep, snap *Snapshot) (bool, error) {
	if snap == nil {
		return false, nil
	}

	table := snap.Tables[step.Table]
	if table == nil {
		return false, nil
	}
	spec, _ := tableByName(step.Table)

	plan, err := convergePlanFor(table, spec, step)
	if err != nil || len(plan.Statements) == 0 {
		return false, err
	}

	if err = store.ApplyConverge(plan); err != nil {
		return false, err
	}

	return true, nil
}

// noteSchemaChange classifies a schema change and logs it.
func noteSchemaChange(endpoint string, step schemaStep, recorded bool, result *migrateResult) {
	action := "create"
	switch {
	case convergeKind(step.Kind):
		action = "converge"
		result.schemaConverged++
	case recorded:
		action = "repair"
		result.schemaRepaired++
	default:
		result.schemaCreated++
	}
	logger.Info(
		"schema changed, endpoint: %s, action: %s, version: %d, name: %s, object: %s, target: %s",
		endpoint, action, step.Version, step.Name, objectName(step.Kind), schemaTarget(step),
	)
}

// objectName renders a schema object kind for logs.
func objectName(kind objectKind) string {
	switch kind {
	case objectTable:
		return "table"
	case objectColumn:
		return "column"
	case objectIndex:
		return "index"
	case objectColumnDef:
		return "column_definition"
	case objectPrimaryKey:
		return "primary_key"
	default:
		return "unknown"
	}
}

// schemaTarget renders the object a step targets, for logs.
func schemaTarget(step schemaStep) string {
	switch step.Kind {
	case objectColumn, objectColumnDef:
		return step.Table + "." + step.Column
	case objectIndex:
		return step.Table + "." + step.Index
	case objectPrimaryKey:
		return step.Table + ".primary_key"
	default:
		return step.Table
	}
}

// logDataActions logs the chosen action of every default strategy.
func logDataActions(endpoint string, actions []strategyAction) {
	for _, action := range actions {
		logger.Info(
			"default strategy, endpoint: %s, bk_biz_id: %d, trigger_event_name: %s, "+
				"trigger_event_name_reason: %d, action: %s",
			endpoint, action.Seed.BkBizID, action.Seed.TriggerEventName,
			int(action.Seed.TriggerEventNameReason), action.Action,
		)
	}
}

// addDataResult folds one endpoint's data actions into the summary counters.
func addDataResult(result *migrateResult, data dataApplyResult) {
	result.dataUnchanged += data.Unchanged

	for _, action := range data.Actions {
		switch action.Action {
		case actionInitialize:
			result.dataInitialized++
		case actionRepair:
			result.dataRepaired++
		case actionSkip:
			result.dataSkipped++
		case actionKeepDeleted:
			result.dataKeptDeleted++
		}
	}
}

// logMigrateFinished logs one summary line per endpoint.
func logMigrateFinished(endpoint string, result migrateResult) {
	logger.Info(
		"migrate finished, endpoint: %s, schema_unchanged: %d, schema_created: %d, "+
			"schema_repaired: %d, schema_converged: %d, data_unchanged: %d, "+
			"data_initialized: %d, data_repaired: %d, data_skipped: %d, data_kept_deleted: %d",
		endpoint,
		result.schemaUnchanged, result.schemaCreated, result.schemaRepaired, result.schemaConverged,
		result.dataUnchanged, result.dataInitialized, result.dataRepaired,
		result.dataSkipped, result.dataKeptDeleted,
	)
}

// convergePlanFor builds the converge plan owned by one converge step.
func convergePlanFor(table *Table, spec tableSpec, step schemaStep) (convergePlan, error) {
	switch step.Kind {
	case objectColumnDef:
		return convergeColumnDefPlan(table, spec, step)
	case objectPrimaryKey:
		return convergePrimaryKeyPlan(table, spec, step)
	default:
		return convergePlan{}, nil
	}
}

// convergeColumnDefPlan converges one column to the target definition.
func convergeColumnDefPlan(table *Table, spec tableSpec, step schemaStep) (convergePlan, error) {
	if _, ok := table.Columns[step.Column]; !ok {
		return convergePlan{}, fmt.Errorf("column missing, table: %s, column: %s", step.Table, step.Column)
	}

	want := columnByName(spec, step.Column)
	if columnRelation(want, table.Columns[step.Column]) == relSatisfy {
		return convergePlan{}, nil
	}

	return buildColumnPlan(table, spec, want), nil
}

// convergePrimaryKeyPlan converges the primary key to the baseline columns.
func convergePrimaryKeyPlan(table *Table, spec tableSpec, step schemaStep) (convergePlan, error) {
	for _, name := range spec.Baseline {
		if _, ok := table.Columns[name]; !ok {
			return convergePlan{}, fmt.Errorf("primary key column missing, table: %s, column: %s", step.Table, name)
		}
	}

	if sameCols(table.PK, spec.Baseline) && targetNeedsNothing(table, spec) {
		return convergePlan{}, nil
	}

	return buildPKPlan(table, spec), nil
}

// targetNeedsNothing reports whether the primary key already matches the target.
func targetNeedsNothing(table *Table, spec tableSpec) bool {
	present, conflict := targetPKView(table, spec)
	return present && !conflict
}

// endpointError wraps a stage failure with the endpoint it happened on.
func endpointError(stage string, store Store, err error) error {
	return fmt.Errorf("%s failed, endpoint: %s, errmsg: %w", stage, store.Endpoint(), err)
}

// stepError wraps a stage failure with the endpoint and step version.
func stepError(stage string, store Store, step schemaStep, err error) error {
	return fmt.Errorf(
		"%s failed, endpoint: %s, version: %d, errmsg: %w",
		stage, store.Endpoint(), step.Version, err,
	)
}
